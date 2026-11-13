import logging
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger('apps.payments')


def get_wallet_balance(user):
    from .models import WalletTransaction
    last = WalletTransaction.objects.filter(user=user).order_by('-created_at').first()
    return last.balance_after if last else Decimal('0')


def _locked_wallet_balance(user):
    """
    Must be called inside a transaction.atomic() block. Takes a row lock on the
    user's most recent wallet ledger entry (or on the user row itself if there is
    no history yet) so concurrent credit/debit calls serialize instead of racing.
    """
    from .models import WalletTransaction
    from apps.users.models import User

    last = (
        WalletTransaction.objects.select_for_update()
        .filter(user=user)
        .order_by('-created_at')
        .first()
    )
    if last:
        return last.balance_after
    # No ledger entries yet: lock the user row so two "first ever" transactions
    # for the same user can't both compute a balance of 0 concurrently.
    User.objects.select_for_update().get(pk=user.pk)
    return Decimal('0')


def credit_wallet(user, amount, description, related_payment=None, related_payout=None):
    from .models import WalletTransaction
    amount = Decimal(str(amount))
    with transaction.atomic():
        balance = _locked_wallet_balance(user) + amount
        return WalletTransaction.objects.create(
            user=user, entry_type=WalletTransaction.EntryType.CREDIT, amount=amount,
            balance_after=balance, description=description,
            related_payment=related_payment, related_payout=related_payout,
        )


def allocate_payment_to_invoices(payment, invoices_with_amounts=None):
    """
    Splits `payment` across one or more invoices via PaymentAllocation. If
    `invoices_with_amounts` (a list of (invoice, amount) tuples) isn't given, the full
    payment amount is auto-allocated oldest-due-first across the payer's outstanding
    invoices on the same lease as `payment.invoice`.
    """
    from .models import PaymentAllocation
    from apps.rentals.models import Invoice

    allocations = []
    if invoices_with_amounts:
        for invoice, amount in invoices_with_amounts:
            allocations.append(PaymentAllocation.objects.create(payment=payment, invoice=invoice, amount=amount))
        return allocations

    if not payment.invoice_id:
        return allocations

    remaining = payment.amount
    lease = payment.invoice.lease
    outstanding = Invoice.objects.filter(
        lease=lease, status__in=[Invoice.Status.PENDING, Invoice.Status.PARTIALLY_PAID, Invoice.Status.OVERDUE],
    ).order_by('due_date')

    for invoice in outstanding:
        if remaining <= 0:
            break
        owed = invoice.amount - invoice.amount_paid
        if owed <= 0:
            continue
        apply_amount = min(owed, remaining)
        allocations.append(PaymentAllocation.objects.create(payment=payment, invoice=invoice, amount=apply_amount))
        invoice.amount_paid += apply_amount
        invoice.status = Invoice.Status.PAID if invoice.amount_paid >= invoice.amount else Invoice.Status.PARTIALLY_PAID
        invoice.save(update_fields=['amount_paid', 'status'])
        remaining -= apply_amount

    return allocations


@transaction.atomic
def request_tenant_advance(*, tenant, lease, amount, reason='', invoice=None):
    from .models import TenantAdvance
    advance = TenantAdvance.objects.create(
        tenant=tenant, lease=lease, invoice=invoice, amount=Decimal(str(amount)), reason=reason,
    )
    try:
        from apps.notifications.services import notify_user
        notify_user(
            lease.landlord, title="Rent Assistance Requested",
            message=f"{tenant.get_full_name()} requested a KES {advance.amount:,.2f} rent advance.",
            notification_type='payment',
        )
    except Exception:
        logger.exception("Failed to notify landlord of advance request")
    return advance


@transaction.atomic
def approve_tenant_advance(advance, *, approved_by):
    from .models import TenantAdvance
    advance.status = TenantAdvance.Status.ACTIVE
    advance.approved_by = approved_by
    advance.approved_at = timezone.now()
    advance.save(update_fields=['status', 'approved_by', 'approved_at'])

    if advance.invoice_id:
        invoice = advance.invoice
        invoice.amount_paid += advance.amount
        invoice.status = invoice.Status.PAID if invoice.amount_paid >= invoice.amount else invoice.Status.PARTIALLY_PAID
        invoice.save(update_fields=['amount_paid', 'status'])

    try:
        from apps.notifications.services import notify_user
        notify_user(
            advance.tenant, title="Rent Advance Approved",
            message=f"Your KES {advance.amount:,.2f} rent advance was approved.",
            notification_type='payment', send_sms_too=True,
        )
    except Exception:
        logger.exception("Failed to notify tenant of advance approval")
    return advance


def reject_tenant_advance(advance, *, rejected_by, reason=''):
    from .models import TenantAdvance
    advance.status = TenantAdvance.Status.REJECTED
    advance.approved_by = rejected_by
    advance.approved_at = timezone.now()
    advance.save(update_fields=['status', 'approved_by', 'approved_at'])
    return advance


@transaction.atomic
def repay_tenant_advance(advance, *, amount, payment=None):
    from .models import TenantAdvance, TenantAdvanceRepayment
    amount = Decimal(str(amount))
    TenantAdvanceRepayment.objects.create(advance=advance, payment=payment, amount=amount)
    advance.amount_repaid += amount
    if advance.amount_repaid >= advance.amount:
        advance.status = TenantAdvance.Status.REPAID
    advance.save(update_fields=['amount_repaid', 'status'])
    return advance


@transaction.atomic
def submit_service_provider_invoice(*, job, provider, amount, description='', attachment=None):
    from .models import ServiceProviderInvoice
    invoice = ServiceProviderInvoice.objects.create(
        job=job, provider=provider, amount=Decimal(str(amount)), description=description, attachment=attachment,
    )
    try:
        from apps.notifications.services import notify_user
        notify_user(
            job.posted_by, title="Service Invoice Submitted",
            message=f"{provider.get_full_name()} submitted an invoice for KES {invoice.amount:,.2f} on '{job.title if hasattr(job, 'title') else job}'.",
            notification_type='job',
        )
    except Exception:
        logger.exception("Failed to notify job poster of submitted invoice")
    return invoice


@transaction.atomic
def approve_service_provider_invoice(invoice, *, reviewed_by, notes=''):
    from .models import ServiceProviderInvoice
    invoice.status = ServiceProviderInvoice.Status.APPROVED
    invoice.reviewed_by = reviewed_by
    invoice.review_notes = notes
    invoice.reviewed_at = timezone.now()
    invoice.save(update_fields=['status', 'reviewed_by', 'review_notes', 'reviewed_at'])
    return invoice


def reject_service_provider_invoice(invoice, *, reviewed_by, notes=''):
    from .models import ServiceProviderInvoice
    invoice.status = ServiceProviderInvoice.Status.REJECTED
    invoice.reviewed_by = reviewed_by
    invoice.review_notes = notes
    invoice.reviewed_at = timezone.now()
    invoice.save(update_fields=['status', 'reviewed_by', 'review_notes', 'reviewed_at'])
    try:
        from apps.notifications.services import notify_user
        notify_user(
            invoice.provider, title="Service Invoice Rejected",
            message=f"Your invoice for KES {invoice.amount:,.2f} was rejected: {notes or 'no reason given'}.",
            notification_type='job',
        )
    except Exception:
        logger.exception("Failed to notify provider of invoice rejection")
    return invoice


@transaction.atomic
def pay_service_provider_invoice(invoice, *, initiated_by=None):
    """Approves-then-pays in one step: creates a Payout for an approved invoice and attempts B2C dispatch."""
    from .models import ServiceProviderInvoice, Payout

    if invoice.status != ServiceProviderInvoice.Status.APPROVED:
        raise ValueError("Only approved invoices can be paid out.")

    payout = Payout.objects.create(
        recipient=invoice.provider, amount=invoice.amount,
        phone_number=getattr(invoice.provider, 'phone_number', ''),
    )
    invoice.payout = payout
    invoice.status = ServiceProviderInvoice.Status.PAID
    invoice.save(update_fields=['payout', 'status'])

    try:
        from .mpesa_client import MpesaClient
        client = MpesaClient()
        result = client.b2c_payment(
            phone_number=payout.phone_number, amount=payout.amount,
            remarks=f"FRIDAH service payout {invoice.id}", occasion=str(invoice.id)[:12],
        )
        payout.status = Payout.Status.PROCESSING
        payout.conversation_id = result.get('ConversationID', '')
        payout.save(update_fields=['status', 'conversation_id'])
    except Exception as e:
        logger.warning("Service provider B2C dispatch failed, left pending for manual processing: %s", e)

    try:
        from apps.notifications.services import notify_user
        notify_user(
            invoice.provider, title="Payment Sent",
            message=f"Your invoice for KES {invoice.amount:,.2f} has been paid.",
            notification_type='payment', send_sms_too=True,
        )
    except Exception:
        logger.exception("Failed to notify provider of payout")

    return payout



    from .models import WalletTransaction
    amount = Decimal(str(amount))
    with transaction.atomic():
        balance = _locked_wallet_balance(user) + amount
        return WalletTransaction.objects.create(
            user=user, entry_type=WalletTransaction.EntryType.CREDIT, amount=amount,
            balance_after=balance, description=description,
            related_payment=related_payment, related_payout=related_payout,
        )


def debit_wallet(user, amount, description, related_payment=None, related_payout=None):
    """
    Raises ValueError if the debit would overdraw the wallet. The balance check and
    the debit happen under the same row lock, so this is safe against concurrent
    debits/payout requests for the same user (see PayoutRequestView).
    """
    from .models import WalletTransaction
    amount = Decimal(str(amount))
    with transaction.atomic():
        current = _locked_wallet_balance(user)
        if amount > current:
            raise ValueError(f"Insufficient wallet balance: have {current}, need {amount}")
        balance = current - amount
        return WalletTransaction.objects.create(
            user=user, entry_type=WalletTransaction.EntryType.DEBIT, amount=amount,
            balance_after=balance, description=description,
            related_payment=related_payment, related_payout=related_payout,
        )


@transaction.atomic
@transaction.atomic
def mark_payment_completed(payment, mpesa_receipt=None, received_amount=None):
    """
    Called once an STK callback (or the polling fallback) confirms success.
    Applies the payment to its linked invoice/booking and credits the recipient's wallet
    net of platform commission.

    Safe to call more than once for the same payment (Safaricom retries callbacks, and the
    Celery poller can race the callback): the row is locked and a payment that is already
    COMPLETED is returned untouched, so money is never applied or credited twice.

    If the provider reports an amount that differs from what we asked for, nothing is
    applied: the payment is flagged DISPUTED for manual reconciliation.
    """
    from .models import Payment, PaymentAllocation
    payment = Payment.objects.select_for_update().select_related('invoice', 'booking').get(pk=payment.pk)

    if payment.status == Payment.Status.COMPLETED:
        logger.info("Duplicate completion ignored for payment %s", payment.reference)
        return payment
    if payment.status in (Payment.Status.REVERSED, Payment.Status.REFUNDED, Payment.Status.DISPUTED):
        logger.warning("Completion ignored for %s payment %s", payment.status, payment.reference)
        return payment

    if received_amount is not None and Decimal(str(received_amount)) != payment.amount:
        payment.status = Payment.Status.DISPUTED
        payment.failure_reason = (
            f"Amount mismatch: expected KES {payment.amount}, provider reported KES {received_amount}."
        )
        payment.save(update_fields=['status', 'failure_reason'])
        logger.error("Payment %s: %s", payment.reference, payment.failure_reason)
        try:
            from apps.audit.services import log_action
            log_action(actor=None, action='payment.amount_mismatch', target=payment,
                       changes={'expected': str(payment.amount), 'received': str(received_amount),
                                'mpesa_receipt': mpesa_receipt or ''}, severity='critical')
        except Exception:
            logger.exception("Failed to audit payment amount mismatch")
        return payment

    payment.status = Payment.Status.COMPLETED
    payment.completed_at = timezone.now()
    payment.save(update_fields=['status', 'completed_at'])

    recipient = None
    commission = Decimal('0')

    if payment.invoice_id:
        invoice = payment.invoice
        owed = invoice.amount - invoice.amount_paid
        primary_amount = min(owed, payment.amount) if owed > 0 else Decimal('0')

        if primary_amount > 0:
            invoice.amount_paid += primary_amount
            invoice.status = invoice.Status.PAID if invoice.amount_paid >= invoice.amount else invoice.Status.PARTIALLY_PAID
            invoice.save(update_fields=['amount_paid', 'status'])
            PaymentAllocation.objects.create(payment=payment, invoice=invoice, amount=primary_amount)
            _generate_receipt(invoice)

        overflow = payment.amount - primary_amount
        if overflow > 0:
            # Payment exceeds what was owed on its primary invoice: sweep the rest across
            # any other outstanding invoices on the same lease, oldest-due-first.
            _sweep_overflow_to_other_invoices(payment, invoice.lease, overflow, exclude_invoice=invoice)

        recipient = invoice.lease.landlord

    elif payment.booking_id:
        booking = payment.booking
        booking.status = booking.Status.CONFIRMED
        booking.amount_paid = (booking.amount_paid or 0) + payment.amount
        booking.save(update_fields=['status', 'amount_paid'])
        recipient = booking.host

    if recipient:
        commission = (payment.amount * Decimal(str(settings.PLATFORM_COMMISSION_PERCENT)) / Decimal('100')).quantize(Decimal('0.01'))
        net_amount = payment.amount - commission
        credit_wallet(recipient, net_amount, f"Payment received: {payment.reference}", related_payment=payment)

    _notify_payment_success(payment)
    return payment


def _sweep_overflow_to_other_invoices(payment, lease, overflow_amount, exclude_invoice=None):
    from apps.rentals.models import Invoice
    from .models import PaymentAllocation

    remaining = overflow_amount
    outstanding = Invoice.objects.filter(
        lease=lease, status__in=[Invoice.Status.PENDING, Invoice.Status.PARTIALLY_PAID, Invoice.Status.OVERDUE],
    ).order_by('due_date')
    if exclude_invoice:
        outstanding = outstanding.exclude(id=exclude_invoice.id)

    for invoice in outstanding:
        if remaining <= 0:
            break
        owed = invoice.amount - invoice.amount_paid
        if owed <= 0:
            continue
        apply_amount = min(owed, remaining)
        PaymentAllocation.objects.create(payment=payment, invoice=invoice, amount=apply_amount)
        invoice.amount_paid += apply_amount
        invoice.status = Invoice.Status.PAID if invoice.amount_paid >= invoice.amount else Invoice.Status.PARTIALLY_PAID
        invoice.save(update_fields=['amount_paid', 'status'])
        remaining -= apply_amount


def mark_payment_failed(payment, reason=""):
    from .models import Payment
    payment.refresh_from_db(fields=['status'])
    if payment.status not in (Payment.Status.PENDING, Payment.Status.PROCESSING):
        # A late or duplicate failure notice must never overwrite a payment that already
        # completed (or was reversed/refunded/disputed).
        logger.info("Failure notice ignored for %s payment %s", payment.status, payment.reference)
        return
    payment.status = Payment.Status.FAILED
    payment.failure_reason = reason
    payment.save(update_fields=['status', 'failure_reason'])
    _notify_payment_failure(payment, reason)


def _generate_receipt(invoice):
    try:
        from .receipts import generate_invoice_receipt
        generate_invoice_receipt(invoice)
    except Exception as e:
        logger.error("Failed to generate PDF receipt for %s: %s", invoice.invoice_number, e)


def _notify_payment_success(payment):
    try:
        from apps.notifications.services import notify_user
        notify_user(
            payment.payer,
            title="Payment Successful",
            message=f"Your payment of KES {payment.amount:,.2f} was received successfully.",
            notification_type="payment",
        )
    except Exception as e:
        logger.error("Notification dispatch failed: %s", e)


def _notify_payment_failure(payment, reason=""):
    try:
        from apps.notifications.services import notify_user
        notify_user(
            payment.payer,
            title="Payment Failed",
            message=(
                f"Your payment of KES {payment.amount:,.2f} could not be completed."
                + (f" Reason: {reason}" if reason else "")
            ),
            notification_type="payment",
        )
    except Exception as e:
        logger.error("Notification dispatch failed: %s", e)


def reconcile_paybill_transaction(txn):
    """
    Attempts to auto-match a PaybillTransaction (raw M-Pesa C2B confirmation) to an
    invoice using the AccountReference the payer typed in when paying, and applies the
    payment if a match is found. Tenants are told to use their invoice number
    (e.g. INV-4F2A9C1B3D) as the paybill account number.

    Returns the (possibly updated) PaybillTransaction.
    """
    from .models import PaybillTransaction, Payment
    from apps.rentals.models import Invoice

    # Guard against Safaricom retrying a confirmation delivery - a receipt number is
    # globally unique per real-world transaction.
    existing = PaybillTransaction.objects.filter(
        mpesa_receipt_number=txn.mpesa_receipt_number
    ).exclude(pk=txn.pk).first()
    if existing:
        txn.match_status = PaybillTransaction.MatchStatus.DUPLICATE
        txn.save(update_fields=['match_status'])
        return txn

    candidate_ref = (txn.bill_ref_number or '').strip().upper()
    txn.invoice_number = candidate_ref

    invoice = Invoice.objects.filter(invoice_number__iexact=candidate_ref).first()
    if not invoice:
        txn.match_status = PaybillTransaction.MatchStatus.UNMATCHED
        txn.save(update_fields=['match_status', 'invoice_number'])
        logger.warning(
            "Paybill payment KES %s (receipt %s) could not be matched to an invoice "
            "(account ref: '%s')", txn.amount, txn.mpesa_receipt_number, txn.bill_ref_number,
        )
        return txn

    payment = Payment.objects.create(
        payer=invoice.tenant,
        invoice=invoice,
        method=Payment.Method.MPESA_C2B,
        status=Payment.Status.PROCESSING,
        amount=txn.amount,
        phone_number=txn.msisdn,
        description=f"Paybill payment for {invoice.invoice_number}",
    )
    mark_payment_completed(payment, mpesa_receipt=txn.mpesa_receipt_number)

    txn.match_status = PaybillTransaction.MatchStatus.MATCHED
    txn.matched_invoice = invoice
    txn.matched_payment = payment
    txn.reconciled_at = timezone.now()
    txn.save(update_fields=[
        'match_status', 'matched_invoice', 'matched_payment', 'reconciled_at', 'invoice_number',
    ])
    return txn


def manually_reconcile_paybill_transaction(txn, invoice, staff_user):
    """Admin manually matches an unmatched/ambiguous paybill payment to an invoice."""
    from .models import Payment

    if txn.match_status == txn.MatchStatus.MATCHED:
        raise ValueError("This transaction is already matched.")

    payment = Payment.objects.create(
        payer=invoice.tenant,
        invoice=invoice,
        method=Payment.Method.MPESA_C2B,
        status=Payment.Status.PROCESSING,
        amount=txn.amount,
        phone_number=txn.msisdn,
        description=f"Paybill payment for {invoice.invoice_number} (manually reconciled)",
    )
    mark_payment_completed(payment, mpesa_receipt=txn.mpesa_receipt_number)

    txn.match_status = txn.MatchStatus.MATCHED
    txn.matched_invoice = invoice
    txn.matched_payment = payment
    txn.reconciled_by = staff_user
    txn.reconciled_at = timezone.now()
    txn.save(update_fields=[
        'match_status', 'matched_invoice', 'matched_payment', 'reconciled_by', 'reconciled_at',
    ])
    return txn
    try:
        from apps.notifications.services import notify_user
        notify_user(
            payment.payer,
            title="Payment Failed",
            message=f"Your payment of KES {payment.amount:,.2f} could not be completed. {reason}",
            notification_type="payment",
        )
    except Exception as e:
        logger.error("Notification dispatch failed: %s", e)


@transaction.atomic
def resolve_disputed_payment(payment, admin, action, reason):
    """
    Administrator resolution of a payment flagged DISPUTED (provider amount != requested amount).

    confirm - the admin checked the Safaricom statement and the expected amount really was
              received: the payment is applied exactly once through the normal path.
    void    - the money did not match or must not be applied: the payment is marked REVERSED
              and nothing is credited; any refund to the customer is handled outside the platform.
    A reason is mandatory and the decision is written to the audit log.
    """
    from django.core.exceptions import ValidationError
    from .models import Payment
    if not (reason or '').strip():
        raise ValidationError('A reason is required to resolve a disputed payment.')
    if action not in ('confirm', 'void'):
        raise ValidationError('Invalid action.')
    payment = Payment.objects.select_for_update().get(pk=payment.pk)
    if payment.status != Payment.Status.DISPUTED:
        raise ValidationError('Only a disputed payment can be resolved.')

    if action == 'confirm':
        payment.status = Payment.Status.PENDING
        payment.failure_reason = ''
        payment.save(update_fields=['status', 'failure_reason'])
        payment = mark_payment_completed(payment)          # no received_amount: admin has verified it
    else:
        payment.status = Payment.Status.REVERSED
        payment.failure_reason = f'Voided by administrator: {reason}'[:255]
        payment.save(update_fields=['status', 'failure_reason'])
    try:
        from apps.audit.services import log_action
        log_action(actor=admin, action=f'payment.dispute.{action}', target=payment,
                   changes={'reason': reason[:500], 'amount': str(payment.amount)}, severity='warning')
    except Exception:
        logger.exception('Failed to audit dispute resolution')
    return payment


def finalize_b2c_result(payout, result_code, result_desc, receipt, raw):
    """
    Apply a B2C result callback to a payout. Must be called with the payout row locked.

    Safe to call repeatedly (Safaricom retries callbacks): once a payout has reached COMPLETED or FAILED
    it is never changed again, and a failed wallet-funded payout is credited back exactly once.
    Refund payouts are paid from the platform's float, not a recipient wallet, so a failure
    credits nothing - the refund simply stays "approved" for a retry or a manual payout.
    """
    from django.utils import timezone
    from .models import Payout, WalletTransaction
    if payout.status in (Payout.Status.COMPLETED, Payout.Status.FAILED):
        logger.info("Duplicate B2C result ignored for payout %s (%s)", payout.id, payout.status)
        return payout

    payout.result_code, payout.result_desc, payout.raw_callback = result_code, result_desc, raw
    if result_code == 0:
        payout.status = Payout.Status.COMPLETED
        payout.transaction_id = receipt
        payout.completed_at = timezone.now()
    else:
        payout.status = Payout.Status.FAILED
        debited = WalletTransaction.objects.filter(related_payout=payout, entry_type=WalletTransaction.EntryType.DEBIT).exists()
        already_returned = WalletTransaction.objects.filter(related_payout=payout, entry_type=WalletTransaction.EntryType.CREDIT).exists()
        if debited and not already_returned:
            credit_wallet(payout.recipient, payout.amount, f"Payout {payout.id} reversed: {result_desc}", related_payout=payout)
    payout.save()

    if payout.refund_id:
        from .refunds import on_refund_payout_result
        on_refund_payout_result(payout)
    return payout
