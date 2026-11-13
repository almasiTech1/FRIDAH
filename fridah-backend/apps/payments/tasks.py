import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger('apps.payments')


@shared_task(bind=True, max_retries=8)
def poll_stk_status(self, payment_id):
    """
    Backup mechanism: polls Daraja directly in case the callback never arrives
    (network issues, Safaricom delays). Scheduled a few times after STK push is sent.
    """
    from .models import Payment, MpesaTransaction
    from .mpesa_client import MpesaClient, MpesaError
    from .services import mark_payment_completed, mark_payment_failed

    try:
        payment = Payment.objects.get(id=payment_id)
    except Payment.DoesNotExist:
        return

    if payment.status != Payment.Status.PROCESSING:
        return  # already resolved by callback

    try:
        mpesa_txn = payment.mpesa_transaction
    except MpesaTransaction.DoesNotExist:
        return

    if not mpesa_txn.checkout_request_id:
        return

    mpesa_txn.poll_count += 1
    mpesa_txn.save(update_fields=['poll_count'])

    if mpesa_txn.poll_count > 6:
        mark_payment_failed(payment, "Payment timed out — no confirmation received.")
        return

    try:
        client = MpesaClient()
        result = client.stk_query(mpesa_txn.checkout_request_id)
        result_code = result.get('ResultCode')
        if result_code is None:
            # still processing on Safaricom's side; retry later
            raise self.retry(countdown=15)
        if str(result_code) == '0':
            mpesa_txn.result_code = 0
            mpesa_txn.result_desc = result.get('ResultDesc')
            mpesa_txn.save(update_fields=['result_code', 'result_desc'])
            mark_payment_completed(payment)
        else:
            mark_payment_failed(payment, result.get('ResultDesc', 'Payment failed or was cancelled.'))
    except MpesaError as e:
        logger.error("STK poll error for payment %s: %s", payment_id, e)
        raise self.retry(countdown=20, exc=e)


@shared_task
def generate_monthly_rent_invoices():
    """Run on the 1st of every month via Celery Beat: creates rent invoices for all active leases."""
    from apps.rentals.models import Lease, Invoice
    from dateutil.relativedelta import relativedelta

    today = timezone.now().date()
    period_start = today.replace(day=1)
    period_end = (period_start + relativedelta(months=1)) - timezone.timedelta(days=1)

    created = 0
    for lease in Lease.objects.filter(status=Lease.Status.ACTIVE):
        if Invoice.objects.filter(lease=lease, period_start=period_start, invoice_type=Invoice.InvoiceType.RENT).exists():
            continue
        due_date = period_start.replace(day=min(lease.rent_due_day, 28))
        Invoice.objects.create(
            lease=lease, tenant=lease.tenant, invoice_type=Invoice.InvoiceType.RENT,
            amount=lease.rent_amount, period_start=period_start, period_end=period_end, due_date=due_date,
        )
        created += 1
    logger.info("Generated %d monthly rent invoices.", created)
    return created


@shared_task
def apply_late_payment_penalties():
    """Run daily: flags overdue invoices and applies a penalty invoice past the grace period."""
    from django.conf import settings
    from apps.rentals.models import Invoice

    today = timezone.now().date()
    grace_cutoff_days = settings.LATE_PAYMENT_GRACE_DAYS
    penalty_pct = settings.LATE_PAYMENT_PENALTY_PERCENT

    overdue_qs = Invoice.objects.filter(
        status__in=[Invoice.Status.PENDING, Invoice.Status.PARTIALLY_PAID],
        due_date__lt=today,
    )
    flagged = 0
    penalized = 0
    for invoice in overdue_qs:
        invoice.status = Invoice.Status.OVERDUE
        invoice.save(update_fields=['status'])
        flagged += 1

        days_overdue = (today - invoice.due_date).days
        if days_overdue == grace_cutoff_days:
            penalty_amount = (invoice.amount * penalty_pct / 100).quantize(invoice.amount)
            Invoice.objects.create(
                lease=invoice.lease, tenant=invoice.tenant, invoice_type=Invoice.InvoiceType.PENALTY,
                amount=penalty_amount, period_start=invoice.period_start, period_end=invoice.period_end,
                due_date=today,
            )
            penalized += 1
    logger.info("Flagged %d overdue invoices, applied %d penalties.", flagged, penalized)
    return {'flagged': flagged, 'penalized': penalized}


@shared_task
def send_payment_reminders():
    """
    Hourly tenant reminder engine (report 3.10). For every unpaid invoice it sends a reminder
    at 7/3/1 days before the due date, on the due date, and on the first day it is overdue -
    each exactly once per invoice (RentReminderLog), so the hourly schedule never double-sends.

    * Works for any charge type (rent, amenity, utility...) and states the outstanding BALANCE.
    * Respects the tenant's payment_alerts preference and quiet hours: during quiet hours the
      reminder is simply not sent yet (and not logged), so the next run after the window sends it.
    * Every message carries a deep link to the invoice and never any payment credentials.
    * One failing invoice never stops the others; failures are logged.
    """
    from apps.rentals.models import Invoice
    from apps.notifications.services import notify_user, in_quiet_hours
    from apps.notifications.models import RentReminderLog

    today = timezone.localdate()
    Trigger = RentReminderLog.Trigger
    open_states = [Invoice.Status.PENDING, Invoice.Status.PARTIALLY_PAID]

    def label(inv):
        return {'rent': 'rent', 'deposit': 'deposit', 'utility': 'utility bill', 'amenity': 'amenity charge'}.get(
            inv.invoice_type, 'invoice')

    def amount(inv):
        return f"KES {inv.balance:,.2f}"

    plan = [
        (today + timezone.timedelta(days=7), Trigger.DUE_IN_7_DAYS, 'Payment due soon',
         lambda i: f"Your {label(i)} of {amount(i)} is due in 7 days ({i.due_date}). Plan ahead to avoid late fees."),
        (today + timezone.timedelta(days=3), Trigger.DUE_IN_3_DAYS, 'Payment due in 3 days',
         lambda i: f"Reminder: your {label(i)} of {amount(i)} is due in 3 days ({i.due_date})."),
        (today + timezone.timedelta(days=1), Trigger.DUE_IN_1_DAY, 'Payment due tomorrow',
         lambda i: f"Your {label(i)} of {amount(i)} is due tomorrow ({i.due_date})."),
        (today, Trigger.DUE_TODAY, 'Payment due today',
         lambda i: f"Your {label(i)} of {amount(i)} is due today."),
    ]

    stats = {'sent': 0, 'held_quiet_hours': 0, 'failed': 0}

    def send(invoice, trigger, title, text):
        try:
            if in_quiet_hours(invoice.tenant):
                stats['held_quiet_hours'] += 1
                return
            notify_user(
                invoice.tenant, title=title, message=text, notification_type='payment', send_sms_too=True,
                alert_category='payment',
                metadata={'invoice_id': str(invoice.id), 'trigger': trigger,
                          'deeplink': f'/tenant/invoices?invoice={invoice.id}'},
            )
            RentReminderLog.objects.get_or_create(invoice=invoice, trigger=trigger)
            stats['sent'] += 1
        except Exception:
            stats['failed'] += 1
            logger.exception('Reminder failed for invoice %s (%s)', invoice.id, trigger)

    for target_date, trigger, title, message_fn in plan:
        invoices = Invoice.objects.filter(status__in=open_states, due_date=target_date).exclude(
            reminder_logs__trigger=trigger).select_related('tenant')
        for invoice in invoices:
            send(invoice, trigger, title, message_fn(invoice))

    # Overdue: fire once, the first time an invoice is flagged overdue.
    overdue = Invoice.objects.filter(status=Invoice.Status.OVERDUE).exclude(
        reminder_logs__trigger=Trigger.OVERDUE).select_related('tenant')
    for invoice in overdue:
        days = (today - invoice.due_date).days
        send(invoice, Trigger.OVERDUE, 'Payment overdue',
             f"Your {label(invoice)} of {amount(invoice)} is now {days} day(s) overdue. "
             f"Please pay to avoid further penalties.")

    logger.info("Reminder engine: %s", stats)
    return stats


@shared_task
def run_daily_reconciliation():
    """Internal books check for yesterday; tells administrators when something needs attention."""
    from datetime import timedelta
    from .reconciliation import run_internal_checks
    day = timezone.localdate() - timedelta(days=1)
    run = run_internal_checks(day, day)
    if run.issues:
        try:
            from django.contrib.auth import get_user_model
            from apps.notifications.services import notify_user
            for admin in get_user_model().objects.filter(role='admin', is_active=True):
                notify_user(admin, 'Reconciliation found issues',
                            f'{run.issues} item(s) need attention for {day}.', notification_type='payment',
                            send_push=False, metadata={'run_id': str(run.id), 'deeplink': '/admin/reconciliation'})
        except Exception:
            logger.exception('Failed to notify admins about reconciliation issues')
    return {'run': str(run.id), 'checked': run.rows_checked, 'issues': run.issues}
