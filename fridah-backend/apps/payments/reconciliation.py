"""
Reconciliation and settlement reporting.

Two kinds of run, each producing a ReconciliationRun with one ReconciliationItem per discrepancy
(items stay open until an administrator resolves them with a note):

* internal  - the platform checks its own books: every completed payment must have exactly one
              wallet credit of the right size (after refunds); payments stuck pending, disputed
              payments and approved-but-unpaid refunds are surfaced.
* statement - an administrator uploads the Safaricom statement (CSV). Each line is matched to a
              platform payment by M-Pesa receipt number; amount differences, money that arrived on
              the paybill but is not on the platform, and platform payments missing from the
              statement are reported.

This deliberately does not call the Daraja API: reconciliation is driven by the official statement
the finance team already holds, which works the same in sandbox and production.
"""
import csv
import io
import logging
from datetime import timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.utils import timezone

from .models import (
    MpesaTransaction, PaybillTransaction, Payment, Payout, ReconciliationItem, ReconciliationRun, Refund, WalletTransaction,
)
from .refunds import recipient_of

logger = logging.getLogger(__name__)
TWO = Decimal('0.01')
TOLERANCE = Decimal('0.02')
K = ReconciliationItem.Kind


def _q(v):
    return Decimal(str(v)).quantize(TWO, rounding=ROUND_HALF_UP)


# --------------------------------------------------------------------------- internal checks
@transaction.atomic
def run_internal_checks(start, end, created_by=None):
    run = ReconciliationRun.objects.create(
        source=ReconciliationRun.Source.INTERNAL, period_start=start, period_end=end, created_by=created_by,
    )
    pct = Decimal(str(settings.PLATFORM_COMMISSION_PERCENT))
    items, flagged = [], set()

    payments = (Payment.objects.filter(status__in=[Payment.Status.COMPLETED, Payment.Status.REFUNDED],
                                       completed_at__date__gte=start, completed_at__date__lte=end)
                .select_related('invoice__lease__landlord', 'booking__host'))
    checked = 0
    for p in payments:
        recipient = recipient_of(p)
        if recipient is None:
            continue
        checked += 1
        entries = WalletTransaction.objects.filter(related_payment=p, user=recipient)
        credits = entries.filter(entry_type=WalletTransaction.EntryType.CREDIT)
        n_credits = credits.count()
        if n_credits == 0:
            items.append(ReconciliationItem(run=run, kind=K.MISSING_WALLET_CREDIT, payment=p, expected_amount=_q(p.amount),
                         note=f'{p.reference}: no wallet credit recorded for the recipient'))
            flagged.add(p.id)
            continue
        if n_credits > 1:
            items.append(ReconciliationItem(run=run, kind=K.DUPLICATE_WALLET_CREDIT, payment=p, expected_amount=_q(p.amount),
                         actual_amount=_q(credits.aggregate(t=Sum('amount'))['t']),
                         note=f'{p.reference}: wallet credited {n_credits} times'))
            flagged.add(p.id)
            continue
        ledger_net = (credits.aggregate(t=Sum('amount'))['t'] or 0) - (
            entries.filter(entry_type=WalletTransaction.EntryType.DEBIT).aggregate(t=Sum('amount'))['t'] or 0)
        net = p.amount - _q(p.amount * pct / 100)
        expected = _q(net * (p.amount - p.refunded_amount) / p.amount) if p.amount else Decimal('0')
        if abs(_q(ledger_net) - expected) > TOLERANCE:
            items.append(ReconciliationItem(run=run, kind=K.WALLET_AMOUNT_MISMATCH, payment=p, expected_amount=expected,
                         actual_amount=_q(ledger_net),
                         note=f'{p.reference}: wallet holds KES {_q(ledger_net)} from this payment, expected KES {expected}'))
            flagged.add(p.id)

    now = timezone.now()
    for p in Payment.objects.filter(status__in=[Payment.Status.PENDING, Payment.Status.PROCESSING],
                                    created_at__lt=now - timedelta(hours=1),
                                    created_at__date__gte=start - timedelta(days=7)):
        items.append(ReconciliationItem(run=run, kind=K.STUCK_PAYMENT, payment=p, expected_amount=_q(p.amount),
                     note=f'{p.reference}: still {p.status} after more than an hour'))
        flagged.add(p.id)
    for p in Payment.objects.filter(status=Payment.Status.DISPUTED):
        items.append(ReconciliationItem(run=run, kind=K.DISPUTED_PAYMENT, payment=p, expected_amount=_q(p.amount),
                     note=f'{p.reference}: {p.failure_reason[:150]}'))
        flagged.add(p.id)
    for r in Refund.objects.filter(status=Refund.Status.APPROVED, decided_at__lt=now - timedelta(days=3)).select_related('payment'):
        items.append(ReconciliationItem(run=run, kind=K.UNPAID_REFUND, payment=r.payment, expected_amount=r.amount,
                     note=f'Approved {r.decided_at:%Y-%m-%d}, customer not yet paid back (payment {r.payment.reference})'))
        flagged.add(r.payment_id)

    ReconciliationItem.objects.bulk_create(items)
    run.rows_checked, run.issues = checked, len(items)
    run.matched = max(checked - len([f for f in flagged]), 0)
    run.save(update_fields=['rows_checked', 'issues', 'matched'])
    return run


# --------------------------------------------------------------------------- statement import
RECEIPT_HEADERS = ('receipt no.', 'receipt no', 'receipt', 'receipt number', 'mpesa receipt', 'transaction id', 'trans id',
                   'transid', 'transaction code', 'mpesareceiptnumber')
AMOUNT_HEADERS = ('paid in', 'amount', 'credit', 'transamount', 'transaction amount', 'amount paid')


def _num(text):
    cleaned = (text or '').replace(',', '').replace('KES', '').replace('Ksh', '').strip()
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def parse_statement_csv(content):
    """Return (rows, skipped). Raises ValidationError if the receipt/amount columns cannot be found."""
    if isinstance(content, bytes):
        content = content.decode('utf-8-sig', errors='replace')
    lines = content.splitlines()
    header_idx = None
    for i, line in enumerate(lines[:30]):      # Safaricom exports have a few title lines first
        cells = [c.strip().lower() for c in next(csv.reader([line]), [])]
        if any(c in RECEIPT_HEADERS for c in cells) and any(c in AMOUNT_HEADERS for c in cells):
            header_idx = i
            break
    if header_idx is None:
        raise ValidationError('Could not find the receipt number and amount columns in this file.')
    reader = csv.DictReader(io.StringIO('\n'.join(lines[header_idx:])))
    fields = {(f or '').strip().lower(): f for f in reader.fieldnames or []}
    rcol = next(fields[h] for h in RECEIPT_HEADERS if h in fields)
    acol = next(fields[h] for h in AMOUNT_HEADERS if h in fields)
    rows, skipped = [], 0
    for rec in reader:
        receipt = (rec.get(rcol) or '').strip()
        amount = _num(rec.get(acol))
        if not receipt or amount is None or amount <= 0:   # withdrawals/charges/blank lines are not receipts
            skipped += 1
            continue
        rows.append({'receipt': receipt.upper(), 'amount': _q(amount)})
    return rows, skipped


@transaction.atomic
def reconcile_statement(rows, start, end, created_by=None, file_name=''):
    run = ReconciliationRun.objects.create(
        source=ReconciliationRun.Source.STATEMENT, period_start=start, period_end=end, created_by=created_by,
        file_name=file_name[:255],
    )
    items, matched, seen = [], 0, set()
    for row in rows:
        receipt, amount = row['receipt'], row['amount']
        seen.add(receipt)
        txn = MpesaTransaction.objects.filter(mpesa_receipt_number__iexact=receipt).select_related('payment').first()
        payment = txn.payment if txn else None
        if payment is None:
            pb = PaybillTransaction.objects.filter(mpesa_receipt_number__iexact=receipt).select_related('matched_payment').first()
            if pb is not None:
                payment = pb.matched_payment
                if payment is None:
                    items.append(ReconciliationItem(run=run, kind=K.MISSING_IN_PLATFORM, receipt=receipt, actual_amount=amount,
                                 note='Received on the paybill but not matched to any invoice'))
                    continue
        if payment is None:
            items.append(ReconciliationItem(run=run, kind=K.MISSING_IN_PLATFORM, receipt=receipt, actual_amount=amount,
                         note='In the statement but not recorded on the platform'))
        elif _q(payment.amount) != amount:
            items.append(ReconciliationItem(run=run, kind=K.AMOUNT_MISMATCH, receipt=receipt, payment=payment,
                         expected_amount=_q(payment.amount), actual_amount=amount,
                         note=f'{payment.reference}: platform KES {_q(payment.amount)} vs statement KES {amount}'))
        else:
            matched += 1

    # Platform-side: completed M-Pesa payments in the period that the statement does not contain.
    in_period = Q(completed_at__date__gte=start, completed_at__date__lte=end,
                  status__in=[Payment.Status.COMPLETED, Payment.Status.REFUNDED])
    for txn in MpesaTransaction.objects.filter(payment__in=Payment.objects.filter(in_period)).exclude(mpesa_receipt_number__isnull=True).exclude(mpesa_receipt_number='').select_related('payment'):
        if txn.mpesa_receipt_number.upper() not in seen:
            items.append(ReconciliationItem(run=run, kind=K.MISSING_IN_STATEMENT, receipt=txn.mpesa_receipt_number,
                         payment=txn.payment, expected_amount=_q(txn.payment.amount),
                         note=f'{txn.payment.reference}: recorded as paid but not in the statement'))
    for pb in PaybillTransaction.objects.filter(matched_payment__in=Payment.objects.filter(in_period)).select_related('matched_payment'):
        if pb.mpesa_receipt_number.upper() not in seen:
            items.append(ReconciliationItem(run=run, kind=K.MISSING_IN_STATEMENT, receipt=pb.mpesa_receipt_number,
                         payment=pb.matched_payment, expected_amount=_q(pb.matched_payment.amount),
                         note=f'{pb.matched_payment.reference}: paybill payment not in the statement'))

    ReconciliationItem.objects.bulk_create(items)
    run.rows_checked, run.matched, run.issues = len(rows), matched, len(items)
    run.save(update_fields=['rows_checked', 'matched', 'issues'])
    return run


@transaction.atomic
def resolve_item(item, user, note):
    if not (note or '').strip():
        raise ValidationError('A resolution note is required.')
    item = ReconciliationItem.objects.select_for_update().get(pk=item.pk)
    if item.resolved:
        raise ValidationError('This item is already resolved.')
    item.resolved, item.resolution_note, item.resolved_by, item.resolved_at = True, note.strip(), user, timezone.now()
    item.save()
    try:
        from apps.audit.services import log_action
        log_action(actor=user, action='reconciliation.item_resolved', target=item,
                   changes={'kind': item.kind, 'note': note[:300], 'receipt': item.receipt})
    except Exception:
        logger.exception('Failed to audit reconciliation resolution')
    return item


# --------------------------------------------------------------------------- settlement summary
def settlement_summary(start, end):
    """
    Platform position for a period: what was collected, what the platform kept, what was credited to
    recipients, refunds applied, payouts sent, and what the platform currently owes in wallets.
    """
    pct = Decimal(str(settings.PLATFORM_COMMISSION_PERCENT))
    paid = Payment.objects.filter(status__in=[Payment.Status.COMPLETED, Payment.Status.REFUNDED],
                                  completed_at__date__gte=start, completed_at__date__lte=end)
    gross = paid.aggregate(t=Sum('amount'))['t'] or Decimal('0')
    credited = (WalletTransaction.objects.filter(related_payment__in=paid, entry_type='credit')
                .aggregate(t=Sum('amount'))['t'] or Decimal('0'))
    refunds = Refund.objects.filter(status__in=[Refund.Status.APPROVED, Refund.Status.PAID_OUT],
                                    decided_at__date__gte=start, decided_at__date__lte=end)
    refunded = refunds.aggregate(t=Sum('amount'))['t'] or Decimal('0')
    refunded_paid = refunds.filter(status=Refund.Status.PAID_OUT).aggregate(t=Sum('amount'))['t'] or Decimal('0')
    recovered = refunds.aggregate(t=Sum('recipient_debit'))['t'] or Decimal('0')
    payouts = Payout.objects.filter(status=Payout.Status.COMPLETED, created_at__date__gte=start, created_at__date__lte=end)
    sent = payouts.aggregate(t=Sum('amount'))['t'] or Decimal('0')

    credits_all = WalletTransaction.objects.filter(entry_type='credit').aggregate(t=Sum('amount'))['t'] or Decimal('0')
    debits_all = WalletTransaction.objects.filter(entry_type='debit').aggregate(t=Sum('amount'))['t'] or Decimal('0')

    daily = list(paid.values('completed_at__date').annotate(payments=Count('id'), gross=Sum('amount')).order_by('completed_at__date'))
    return {
        'period': {'start': str(start), 'end': str(end)},
        'gross_collected': _q(gross),
        'credited_to_recipients': _q(credited),
        'platform_commission': _q(gross - credited),
        'configured_commission_percent': float(pct),
        'refunds_approved': _q(refunded),
        'refunds_paid_out_to_customers': _q(refunded_paid),
        'refunds_awaiting_payout': _q(refunded - refunded_paid),
        'recovered_from_recipient_wallets': _q(recovered),
        'payouts_sent_to_recipients': _q(sent),
        'wallet_liability': _q(credits_all - debits_all),   # what the platform owes recipients right now
        'daily': [{'date': str(d['completed_at__date']), 'payments': d['payments'], 'gross': _q(d['gross'])} for d in daily],
    }
