"""Amenity billing: idempotent invoice generation and audited waivers."""
import calendar
import logging
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import AmenityCharge, Invoice, Lease

logger = logging.getLogger(__name__)


def _month_bounds(day):
    return day.replace(day=1), day.replace(day=calendar.monthrange(day.year, day.month)[1])


def _due_date(lease, period_start):
    last = calendar.monthrange(period_start.year, period_start.month)[1]
    return period_start.replace(day=min(lease.rent_due_day or 5, last))


def _eligible_leases(charge):
    qs = Lease.objects.filter(unit__property=charge.property, status=Lease.Status.ACTIVE).select_related('tenant', 'unit')
    if not charge.applies_to_all_units:
        qs = qs.filter(unit__in=charge.units.all())
    return qs.exclude(amenity_exemptions__charge=charge)


@transaction.atomic
def generate_for_charge(charge, on_date=None):
    """Bill one charge for the month containing `on_date`. Returns (created, skipped)."""
    if not charge.is_active:
        return 0, 0
    on_date = on_date or timezone.now().date()
    start, end = _month_bounds(on_date)
    created = skipped = 0
    for lease in _eligible_leases(charge):
        if charge.frequency == AmenityCharge.Frequency.ONE_OFF:
            exists = Invoice.objects.filter(amenity_charge=charge, lease=lease).exists()
        else:
            exists = Invoice.objects.filter(amenity_charge=charge, lease=lease, period_start=start).exists()
        if exists or lease.start_date > end:
            skipped += 1
            continue
        Invoice.objects.create(
            lease=lease, tenant=lease.tenant, invoice_type=Invoice.InvoiceType.AMENITY, amount=charge.amount,
            period_start=start, period_end=end, due_date=_due_date(lease, start), amenity_charge=charge,
        )
        created += 1
    return created, skipped


def generate_all(on_date=None):
    """Daily task entry: every active charge on every published property. Failures are isolated."""
    from apps.properties.models import Property
    totals = {'created': 0, 'skipped': 0, 'failed': 0}
    charges = AmenityCharge.objects.filter(is_active=True, property__status=Property.Status.ACTIVE)
    for charge in charges.select_related('property'):
        try:
            c, s = generate_for_charge(charge, on_date)
            totals['created'] += c
            totals['skipped'] += s
        except Exception:
            totals['failed'] += 1
            logger.exception('Amenity billing failed for charge %s', charge.id)
    return totals


@transaction.atomic
def waive_invoice(invoice, actor, reason):
    """Cancel an unpaid amenity invoice with a recorded reason. Paid money is a refund, not a waiver."""
    if not (reason or '').strip():
        raise ValidationError('A reason is required to waive an invoice.')
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if invoice.invoice_type != Invoice.InvoiceType.AMENITY:
        raise ValidationError('Only amenity invoices can be waived here.')
    if invoice.status == Invoice.Status.CANCELLED:
        raise ValidationError('This invoice is already waived/cancelled.')
    if invoice.amount_paid > 0:
        raise ValidationError('This invoice has payments against it; handle it as a refund instead of a waiver.')
    invoice.status = Invoice.Status.CANCELLED
    invoice.waived_at, invoice.waived_by, invoice.waiver_reason = timezone.now(), actor, reason
    invoice.save(update_fields=['status', 'waived_at', 'waived_by', 'waiver_reason', 'updated_at'])
    try:
        from apps.audit.services import log_action
        log_action(actor=actor, action='amenity.invoice.waived', target=invoice,
                   property=invoice.lease.unit.property,
                   changes={'amount': str(invoice.amount), 'reason': reason[:500]}, severity='warning')
    except Exception:
        logger.exception('Failed to audit amenity waiver')
    return invoice
