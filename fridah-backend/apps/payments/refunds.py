"""
Refunds and reversals.

Policy (all configurable in settings, defaults shown):

* REFUND_ADMIN_APPROVAL_ABOVE = 5000   KES. Up to this amount a refund may be approved by the
  payment's recipient (landlord/host) OR an administrator; above it, or for any *reversal*, only a
  platform administrator can approve.
* Maker-checker: nobody approves their own request (REFUND_ALLOW_SELF_APPROVAL = False).
* REFUND_WINDOW_DAYS = 180: refunds can only be requested for payments completed within this window.
* Only COMPLETED payments can be refunded; the total refunded can never exceed the payment amount
  (open requests count against the remaining balance, so two requests cannot over-refund).

Approving a refund immediately reverses the platform's books in one transaction: invoice
allocations (newest first) and invoice status, the booking's paid amount, and the recipient's wallet
(by the same share of the net they were credited). Sending the money back to the customer through
M-Pesa is a separate, recorded step (`mark_refund_paid`) - this module does not call Daraja.
"""
import logging
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import Payment, PaymentAllocation, Refund, WalletTransaction

logger = logging.getLogger(__name__)
TWO = Decimal('0.01')


def _q(v):
    return Decimal(str(v)).quantize(TWO, rounding=ROUND_HALF_UP)


def _is_admin(user):
    return bool(user and user.is_authenticated and (user.role == 'admin' or user.is_staff))


def _policy():
    from .models import RefundPolicy
    return RefundPolicy.objects.filter(pk=1).first()


def admin_limit():
    p = _policy()
    return p.admin_approval_above if p else Decimal(str(getattr(settings, 'REFUND_ADMIN_APPROVAL_ABOVE', 5000)))


def window_days():
    p = _policy()
    return p.window_days if p else int(getattr(settings, 'REFUND_WINDOW_DAYS', 180))


def current_policy():
    return {
        'admin_approval_above': _q(admin_limit()), 'window_days': window_days(),
        'self_approval_allowed': bool(getattr(settings, 'REFUND_ALLOW_SELF_APPROVAL', False)),
        'auto_payout_enabled': auto_payout_enabled(),
    }


@transaction.atomic
def update_policy(admin, admin_approval_above, window):
    """Administrator changes the approval limit / refund window. Recorded in the audit log with before and after."""
    from .models import RefundPolicy
    if not _is_admin(admin):
        raise PermissionDenied('Only an administrator can change the refund policy.')
    try:
        limit = _q(admin_approval_above)
        days = int(window)
    except (ArithmeticError, ValueError, TypeError):
        raise ValidationError('Enter a valid amount and number of days.')
    if limit < 0 or limit > Decimal('1000000'):
        raise ValidationError('The approval limit must be between KES 0 and KES 1,000,000.')
    if days < 1 or days > 730:
        raise ValidationError('The refund window must be between 1 and 730 days.')
    before = current_policy()
    RefundPolicy.objects.update_or_create(pk=1, defaults={'admin_approval_above': limit, 'window_days': days, 'updated_by': admin})
    after = current_policy()
    try:
        from apps.audit.services import log_action
        log_action(actor=admin, action='refund.policy_changed', target=RefundPolicy.objects.get(pk=1),
                   changes={'before': {k: str(v) for k, v in before.items()}, 'after': {k: str(v) for k, v in after.items()}},
                   severity='warning')
    except Exception:
        logger.exception('Failed to audit refund policy change')
    return after


def recipient_of(payment):
    """Who was credited for this payment (the landlord of the invoice's lease, or the booking host)."""
    if payment.invoice_id:
        return payment.invoice.lease.landlord
    if payment.booking_id:
        return payment.booking.host
    return None


def pending_total(payment):
    return payment.refunds.filter(status=Refund.Status.REQUESTED).aggregate(t=Sum('amount'))['t'] or Decimal('0')


def remaining_refundable(payment):
    return payment.amount - payment.refunded_amount - pending_total(payment)


def _log(actor, action, refund, **changes):
    try:
        from apps.audit.services import log_action
        log_action(actor=actor, action=action, target=refund, changes={
            'payment': str(refund.payment_id), 'amount': str(refund.amount), 'kind': refund.kind, **changes,
        }, severity='warning')
    except Exception:
        logger.exception('Failed to audit refund action')


def _notify(user, title, message, refund):
    if user is None:
        return
    try:
        from apps.notifications.services import notify_user
        notify_user(user, title, message, notification_type='payment',
                    metadata={'refund_id': str(refund.id), 'payment_id': str(refund.payment_id)})
    except Exception:
        logger.exception('Failed to send refund notification')


def _admins():
    from django.contrib.auth import get_user_model
    return get_user_model().objects.filter(role='admin', is_active=True)


# --------------------------------------------------------------------------- request
@transaction.atomic
def request_refund(payment, user, amount, reason, kind=Refund.Kind.REFUND):
    payment = Payment.objects.select_for_update().select_related('invoice__lease__landlord', 'booking').get(pk=payment.pk)
    recipient = recipient_of(payment)

    allowed = _is_admin(user) or user.id == payment.payer_id or (recipient and user.id == recipient.id)
    if not allowed:
        raise PermissionDenied('You cannot request a refund for this payment.')
    if kind == Refund.Kind.REVERSAL and not (_is_admin(user) or (recipient and user.id == recipient.id)):
        raise PermissionDenied('Only an administrator or the recipient can request a reversal.')
    if not (reason or '').strip():
        raise ValidationError('A reason is required.')
    if payment.status != Payment.Status.COMPLETED:
        raise ValidationError('Only a completed payment can be refunded.')
    if payment.completed_at and payment.completed_at < timezone.now() - timedelta(days=window_days()):
        raise ValidationError(f'Refunds can only be requested within {window_days()} days of payment.')

    amount = _q(amount)
    if amount <= 0:
        raise ValidationError('Amount must be greater than zero.')
    if kind == Refund.Kind.REVERSAL and amount != _q(payment.amount - payment.refunded_amount):
        raise ValidationError('A reversal must cover the full remaining amount of the payment.')
    remaining = remaining_refundable(payment)
    if amount > remaining:
        raise ValidationError(f'Only KES {remaining} of this payment can still be refunded.')

    admin_only = kind == Refund.Kind.REVERSAL or amount > admin_limit() or recipient is None
    refund = Refund.objects.create(
        payment=payment, kind=kind, amount=amount, reason=reason.strip(), requested_by=user,
        approval_level=Refund.ApprovalLevel.ADMIN if admin_only else Refund.ApprovalLevel.RECIPIENT,
    )
    _log(user, 'refund.requested', refund, level=refund.approval_level)

    label = 'Reversal' if kind == Refund.Kind.REVERSAL else 'Refund'
    for admin in _admins():
        if admin.id != user.id:
            _notify(admin, f'{label} awaiting approval', f'KES {amount} on payment {payment.reference}: {reason[:120]}', refund)
    if not admin_only and recipient and recipient.id != user.id:
        _notify(recipient, f'{label} request needs your approval', f'KES {amount} on payment {payment.reference}.', refund)
    return refund


# --------------------------------------------------------------------------- decide
def _check_can_decide(refund, user):
    recipient = recipient_of(refund.payment)
    if _is_admin(user):
        pass
    elif refund.approval_level == Refund.ApprovalLevel.RECIPIENT and recipient and user.id == recipient.id:
        pass
    else:
        raise PermissionDenied('You are not allowed to decide this request.')
    if refund.requested_by_id == user.id and not getattr(settings, 'REFUND_ALLOW_SELF_APPROVAL', False):
        raise PermissionDenied('You cannot approve or reject your own request; another approver must decide it.')


def _reverse_allocations(payment, amount):
    """Take `amount` back off the invoices this payment settled, most recent allocation first."""
    left = amount
    for alloc in payment.allocations.select_for_update().select_related('invoice').order_by('-created_at'):
        if left <= 0:
            break
        take = min(alloc.amount, left)
        if take <= 0:
            continue
        invoice = alloc.invoice
        invoice.amount_paid = max(Decimal('0'), invoice.amount_paid - take)
        if invoice.amount_paid <= 0:
            invoice.status = (invoice.Status.OVERDUE if invoice.due_date < timezone.localdate() else invoice.Status.PENDING)
        elif invoice.amount_paid < invoice.amount:
            invoice.status = invoice.Status.PARTIALLY_PAID
        invoice.save(update_fields=['amount_paid', 'status'])
        alloc.amount -= take
        alloc.save(update_fields=['amount'])
        left -= take
    if left > 0 and payment.invoice_id and not payment.allocations.exists():
        # Older payments recorded before allocations existed: adjust the primary invoice directly.
        invoice = payment.invoice
        invoice.amount_paid = max(Decimal('0'), invoice.amount_paid - left)
        invoice.status = invoice.Status.PARTIALLY_PAID if invoice.amount_paid > 0 else invoice.Status.PENDING
        invoice.save(update_fields=['amount_paid', 'status'])


def _debit_recipient(payment, recipient, refund, allow_negative):
    from .services import _locked_wallet_balance, debit_wallet
    credited = (WalletTransaction.objects.filter(related_payment=payment, entry_type=WalletTransaction.EntryType.CREDIT)
                .aggregate(t=Sum('amount'))['t'] or Decimal('0'))
    if credited <= 0 or payment.amount <= 0:
        return Decimal('0')
    share = _q(credited * refund.amount / payment.amount)
    description = f'{refund.get_kind_display()}: {payment.reference}'
    try:
        debit_wallet(recipient, share, description, related_payment=payment)
    except ValueError:
        if not allow_negative:
            raise ValidationError(
                'The recipient has already withdrawn funds from this payment, so their wallet cannot cover the refund. '
                'An administrator can approve it with "allow negative balance" to claw it back from future earnings.')
        balance = _locked_wallet_balance(recipient) - share
        WalletTransaction.objects.create(
            user=recipient, entry_type=WalletTransaction.EntryType.DEBIT, amount=share, balance_after=balance,
            description=description + ' (negative balance)', related_payment=payment,
        )
    return share


@transaction.atomic
def approve_refund(refund, user, comment='', allow_negative_balance=False):
    refund = Refund.objects.select_for_update().get(pk=refund.pk)
    payment = (Payment.objects.select_for_update().select_related('invoice__lease__landlord', 'booking__host')
               .get(pk=refund.payment_id))
    refund.payment = payment
    if refund.status != Refund.Status.REQUESTED:
        raise ValidationError('This request has already been decided.')
    _check_can_decide(refund, user)
    if allow_negative_balance and not _is_admin(user):
        raise PermissionDenied('Only an administrator can approve with a negative balance.')
    if payment.status != Payment.Status.COMPLETED or refund.amount > payment.amount - payment.refunded_amount:
        raise ValidationError('This payment can no longer be refunded for that amount.')

    recipient = recipient_of(payment)
    _reverse_allocations(payment, refund.amount)
    if payment.booking_id:
        booking = payment.booking
        booking.amount_paid = max(Decimal('0'), (booking.amount_paid or 0) - refund.amount)
        booking.save(update_fields=['amount_paid'])
    debit = _debit_recipient(payment, recipient, refund, allow_negative_balance) if recipient else Decimal('0')

    payment.refunded_amount += refund.amount
    if payment.refunded_amount >= payment.amount:
        payment.status = Payment.Status.REFUNDED
    payment.save(update_fields=['refunded_amount', 'status'])

    refund.status = Refund.Status.APPROVED
    refund.decided_by, refund.decided_at, refund.decision_comment = user, timezone.now(), comment or ''
    refund.recipient_debit, refund.ledger_applied_at = debit, timezone.now()
    refund.save()
    _log(user, 'refund.approved', refund, recipient_debit=str(debit), comment=(comment or '')[:300])

    msg = f'KES {refund.amount} on payment {payment.reference} was approved.'
    _notify(refund.requested_by, 'Refund approved', msg, refund)
    if payment.payer_id != getattr(refund.requested_by, 'id', None):
        _notify(payment.payer, 'Your refund was approved', msg + ' You will be paid back via M-Pesa.', refund)
    if recipient and recipient.id not in (user.id, getattr(refund.requested_by, 'id', None)):
        _notify(recipient, 'A refund was applied to your account', msg, refund)
    return refund


@transaction.atomic
def reject_refund(refund, user, comment):
    refund = Refund.objects.select_for_update().select_related('payment__invoice__lease__landlord', 'payment__booking').get(pk=refund.pk)
    if refund.status != Refund.Status.REQUESTED:
        raise ValidationError('This request has already been decided.')
    _check_can_decide(refund, user)
    if not (comment or '').strip():
        raise ValidationError('A reason is required to reject a request.')
    refund.status = Refund.Status.REJECTED
    refund.decided_by, refund.decided_at, refund.decision_comment = user, timezone.now(), comment.strip()
    refund.save()
    _log(user, 'refund.rejected', refund, comment=comment[:300])
    _notify(refund.requested_by, 'Refund rejected', f'KES {refund.amount} on payment {refund.payment.reference}: {comment[:150]}', refund)
    return refund


@transaction.atomic
def cancel_refund(refund, user):
    refund = Refund.objects.select_for_update().get(pk=refund.pk)
    if refund.requested_by_id != user.id:
        raise PermissionDenied('Only the requester can cancel a request.')
    if refund.status != Refund.Status.REQUESTED:
        raise ValidationError('Only a pending request can be cancelled.')
    refund.status = Refund.Status.CANCELLED
    refund.save(update_fields=['status'])
    _log(user, 'refund.cancelled', refund)
    return refund


@transaction.atomic
def mark_refund_paid(refund, admin, reference):
    """Record that the customer has been paid back through M-Pesa (outside the platform) with its reference."""
    refund = Refund.objects.select_for_update().get(pk=refund.pk)
    if not _is_admin(admin):
        raise PermissionDenied('Only an administrator can record a payout.')
    if refund.status != Refund.Status.APPROVED:
        raise ValidationError('Only an approved refund can be marked as paid out.')
    reference = (reference or '').strip()
    if len(reference) < 6:
        raise ValidationError('Enter the M-Pesa reference of the payout.')
    if Refund.objects.filter(payout_reference__iexact=reference).exclude(pk=refund.pk).exists():
        raise ValidationError('That payout reference has already been used for another refund.')
    refund.status = Refund.Status.PAID_OUT
    refund.payout_reference, refund.paid_out_by, refund.paid_out_at = reference, admin, timezone.now()
    refund.save()
    _log(admin, 'refund.paid_out', refund, payout_reference=reference)
    _notify(refund.payment.payer, 'Refund paid', f'KES {refund.amount} has been sent to you (ref {reference}).', refund)
    return refund


# --------------------------------------------------------------------------- automatic M-Pesa payout
def auto_payout_enabled():
    return bool(getattr(settings, 'MPESA_B2C_REFUNDS_ENABLED', False))


def initiate_refund_payout(refund, admin, phone_number=None):
    """
    Send an approved refund to the customer through M-Pesa B2C. Off unless MPESA_B2C_REFUNDS_ENABLED is set
    (it spends the business's own float, so finance must switch it on deliberately). The result arrives on
    the B2C result callback, which marks the refund paid out with the M-Pesa receipt.

    The PENDING payout row is committed (under a row lock, so a double click cannot send twice) BEFORE the
    network call, and a failed attempt is kept on record, not rolled back.
    """
    from .models import Payout
    from .mpesa_client import MpesaClient, MpesaError
    if not _is_admin(admin):
        raise PermissionDenied('Only an administrator can send a payout.')
    if not auto_payout_enabled():
        raise ValidationError('Automatic M-Pesa payouts are not enabled. Pay the customer yourself and record the reference.')

    with transaction.atomic():
        refund = Refund.objects.select_for_update().select_related('payment__payer').get(pk=refund.pk)
        if refund.status != Refund.Status.APPROVED:
            raise ValidationError('Only an approved refund can be paid out.')
        if refund.payouts.filter(status__in=[Payout.Status.PENDING, Payout.Status.PROCESSING, Payout.Status.COMPLETED]).exists():
            raise ValidationError('A payout for this refund is already in progress or completed.')
        if refund.amount != refund.amount.to_integral_value():
            raise ValidationError(
                f'M-Pesa B2C pays whole shillings only, and this refund is KES {refund.amount}. '
                'Pay it manually and record the reference.')
        payment = refund.payment
        phone = (phone_number or payment.phone_number or getattr(payment.payer, 'phone_number', '') or '').strip()
        if not phone:
            raise ValidationError('There is no phone number to pay out to.')
        payout = Payout.objects.create(
            recipient=payment.payer, amount=refund.amount, phone_number=phone, status=Payout.Status.PENDING,
            related_payment=payment, refund=refund,
        )

    try:
        result = MpesaClient().b2c_payment(phone_number=phone, amount=refund.amount,
                                           remarks=f'FRIDAH refund {payment.reference}', occasion='Refund')
    except MpesaError as e:
        payout.status, payout.result_desc = Payout.Status.FAILED, str(e)[:500]
        payout.save(update_fields=['status', 'result_desc'])
        _log(admin, 'refund.payout_failed', refund, error=str(e)[:200])
        raise ValidationError(f'M-Pesa rejected the payout: {e}')
    payout.conversation_id = result.get('ConversationID')
    payout.status = Payout.Status.PROCESSING
    payout.save(update_fields=['conversation_id', 'status'])
    _log(admin, 'refund.payout_initiated', refund, payout=str(payout.id), phone=phone[-4:])
    return payout


def on_refund_payout_result(payout):
    """Called from the B2C result callback once a refund payout has completed or failed."""
    from .models import Payout
    refund = Refund.objects.select_for_update().select_related('payment__payer').get(pk=payout.refund_id)
    if payout.status == Payout.Status.COMPLETED and refund.status == Refund.Status.APPROVED:
        refund.status = Refund.Status.PAID_OUT
        refund.payout_reference = payout.transaction_id or str(payout.conversation_id or '')
        refund.paid_out_at = timezone.now()
        refund.save()
        _log(None, 'refund.paid_out', refund, payout_reference=refund.payout_reference, via='mpesa_b2c')
        _notify(refund.payment.payer, 'Refund paid', f'KES {refund.amount} has been sent to your M-Pesa (ref {refund.payout_reference}).', refund)
    elif payout.status == Payout.Status.FAILED:
        _log(None, 'refund.payout_failed', refund, error=(payout.result_desc or '')[:200])
        for admin in _admins():
            _notify(admin, 'Refund payout failed',
                    f'KES {refund.amount} to {refund.payment.payer.get_full_name()} failed: {payout.result_desc}. Retry or pay manually.', refund)
