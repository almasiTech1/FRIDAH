import logging
import uuid
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger('apps.rentals')


@transaction.atomic
def accept_lease_renewal(renewal):
    """
    Tenant accepted: close out the current lease at its end_date and create a fresh
    Lease row for the new term (keeps historical leases/invoices intact rather than
    mutating dates on the old one).
    """
    from .models import Lease, LeaseRenewal

    old_lease = renewal.lease
    new_lease = Lease.objects.create(
        tenant=old_lease.tenant,
        unit=old_lease.unit,
        landlord=old_lease.landlord,
        start_date=renewal.proposed_start_date,
        end_date=renewal.proposed_end_date,
        rent_amount=renewal.proposed_rent_amount,
        deposit_amount=old_lease.deposit_amount,
        deposit_paid=True,  # deposit carries over from the existing tenancy
        rent_due_day=old_lease.rent_due_day,
        status=Lease.Status.ACTIVE if renewal.proposed_start_date <= timezone.now().date() else Lease.Status.PENDING,
    )

    old_lease.status = Lease.Status.EXPIRED
    old_lease.save(update_fields=['status'])

    renewal.status = LeaseRenewal.Status.ACCEPTED
    renewal.responded_at = timezone.now()
    renewal.renewed_lease = new_lease
    renewal.save(update_fields=['status', 'responded_at', 'renewed_lease'])

    _notify_renewal_response(renewal, accepted=True)
    return new_lease


@transaction.atomic
def decline_lease_renewal(renewal, reason=""):
    from .models import LeaseRenewal

    renewal.status = LeaseRenewal.Status.DECLINED
    renewal.responded_at = timezone.now()
    renewal.decline_reason = reason
    renewal.save(update_fields=['status', 'responded_at', 'decline_reason'])

    _notify_renewal_response(renewal, accepted=False)
    return renewal


def _notify_renewal_response(renewal, accepted):
    try:
        from apps.notifications.services import notify_user
        notify_user(
            renewal.lease.landlord,
            title="Lease Renewal Response",
            message=(
                f"{renewal.lease.tenant.get_full_name()} has "
                f"{'accepted' if accepted else 'declined'} the renewal offer for "
                f"{renewal.lease.unit}."
            ),
            notification_type="lease",
        )
    except Exception as e:
        logger.error("Notification dispatch failed: %s", e)


def record_utility_reading(*, utility_account, reading_value, reading_date, recorded_by=None, photo=None):
    """
    Records a meter reading and, if the account is metered with a rate configured,
    automatically generates a utility Invoice for the usage since the last reading.
    Flat-fee (non-metered) utilities generate their invoice separately on a schedule
    (see generate_flat_fee_utility_invoices), since there's no "reading" to derive from.
    """
    from .models import UtilityMeterReading, Invoice, Lease

    previous = (
        UtilityMeterReading.objects.filter(utility_account=utility_account, reading_date__lt=reading_date)
        .order_by('-reading_date')
        .first()
    )

    reading = UtilityMeterReading.objects.create(
        utility_account=utility_account, reading_value=reading_value, reading_date=reading_date,
        recorded_by=recorded_by, photo=photo,
    )

    if not (utility_account.is_metered and utility_account.rate_per_unit and previous):
        return reading, None  # Nothing to bill yet (first reading, or no rate configured).

    usage = reading_value - previous.reading_value
    if usage <= 0:
        logger.warning(
            "Utility reading for %s is not higher than the previous reading (%s <= %s) - skipping invoice.",
            utility_account, reading_value, previous.reading_value,
        )
        return reading, None

    lease = Lease.objects.filter(unit=utility_account.unit, status=Lease.Status.ACTIVE).first()
    if not lease:
        logger.warning("No active lease for %s - can't bill utility usage to a tenant.", utility_account.unit)
        return reading, None

    amount = usage * utility_account.rate_per_unit
    invoice = Invoice.objects.create(
        invoice_number=f"UTIL-{uuid.uuid4().hex[:10].upper()}",
        lease=lease,
        tenant=lease.tenant,
        invoice_type=Invoice.InvoiceType.UTILITY,
        amount=amount,
        period_start=previous.reading_date,
        period_end=reading_date,
        due_date=reading_date + timezone.timedelta(days=14),
        status=Invoice.Status.PENDING,
        description=(
            f"{utility_account.get_utility_type_display()} usage: {usage} units "
            f"({previous.reading_value} → {reading_value}) at KES {utility_account.rate_per_unit}/unit"
        ),
    )
    reading.generated_invoice = invoice
    reading.save(update_fields=['generated_invoice'])
    return reading, invoice


def generate_flat_fee_utility_invoices():
    """Monthly Celery Beat task: bills flat-fee utilities (garbage, often internet) for every active lease."""
    from .models import UtilityAccount, Invoice, Lease

    created = 0
    accounts = UtilityAccount.objects.filter(is_active=True, is_metered=False, flat_monthly_fee__isnull=False)
    for account in accounts:
        lease = Lease.objects.filter(unit=account.unit, status=Lease.Status.ACTIVE).first()
        if not lease:
            continue

        period_start = timezone.now().date().replace(day=1)
        already_billed = Invoice.objects.filter(
            lease=lease, invoice_type=Invoice.InvoiceType.UTILITY, period_start=period_start,
            description__icontains=account.get_utility_type_display(),
        ).exists()
        if already_billed:
            continue

        Invoice.objects.create(
            invoice_number=f"UTIL-{uuid.uuid4().hex[:10].upper()}",
            lease=lease, tenant=lease.tenant, invoice_type=Invoice.InvoiceType.UTILITY,
            amount=account.flat_monthly_fee, period_start=period_start,
            period_end=period_start + timezone.timedelta(days=30),
            due_date=period_start + timezone.timedelta(days=14),
            status=Invoice.Status.PENDING,
            description=f"{account.get_utility_type_display()} - monthly flat fee",
        )
        created += 1
    logger.info("Generated %d flat-fee utility invoices.", created)
    return created


@transaction.atomic
def submit_rental_application(*, unit, tenant, message="", preferred_move_in_date=None):
    from apps.properties.models import Unit
    from .models import RentalApplication

    from apps.properties.models import Property
    if unit.property.status != Property.Status.ACTIVE:
        # Only approved, listed properties can be applied for (an unapproved one is not visible to tenants at all).
        raise ValueError("This property is not currently listed for rent.")
    if unit.status != Unit.Status.VACANT:
        raise ValueError("This unit is not currently vacant.")
    if RentalApplication.objects.filter(unit=unit, tenant=tenant, status=RentalApplication.Status.PENDING).exists():
        raise ValueError("You already have a pending application for this unit.")

    return RentalApplication.objects.create(
        unit=unit, tenant=tenant, message=message, preferred_move_in_date=preferred_move_in_date,
    )


@transaction.atomic
def approve_rental_application(application, *, reviewed_by, rent_amount=None, deposit_amount=None,
                                start_date=None, rent_due_day=5):
    from apps.properties.models import Unit
    from .models import Lease, RentalApplication

    if application.status != RentalApplication.Status.PENDING:
        raise ValueError("Only a pending application can be approved.")

    unit = application.unit
    if unit.status != Unit.Status.VACANT:
        raise ValueError("This unit is no longer vacant.")

    lease = Lease.objects.create(
        tenant=application.tenant, unit=unit, landlord=unit.property.landlord,
        start_date=start_date or timezone.now().date(),
        rent_amount=rent_amount if rent_amount is not None else unit.rent_amount,
        deposit_amount=deposit_amount if deposit_amount is not None else unit.deposit_amount,
        rent_due_day=rent_due_day, status=Lease.Status.ACTIVE,
    )
    unit.status = Unit.Status.OCCUPIED
    unit.save(update_fields=['status'])

    application.status = RentalApplication.Status.APPROVED
    application.resulting_lease = lease
    application.reviewed_by = reviewed_by
    application.reviewed_at = timezone.now()
    application.save(update_fields=['status', 'resulting_lease', 'reviewed_by', 'reviewed_at', 'updated_at'])

    # The unit's taken now - any other still-pending applications for it are moot.
    other_pending = RentalApplication.objects.filter(
        unit=unit, status=RentalApplication.Status.PENDING,
    ).exclude(id=application.id)
    for other in other_pending:
        other.status = RentalApplication.Status.REJECTED
        other.rejection_reason = "Unit was leased to another applicant."
        other.reviewed_by = reviewed_by
        other.reviewed_at = timezone.now()
        other.save(update_fields=['status', 'rejection_reason', 'reviewed_by', 'reviewed_at', 'updated_at'])
        _notify_application_status(other)

    _notify_application_status(application)
    return lease


def reject_rental_application(application, *, reviewed_by, reason=""):
    from .models import RentalApplication
    if application.status != RentalApplication.Status.PENDING:
        raise ValueError("Only a pending application can be rejected.")
    application.status = RentalApplication.Status.REJECTED
    application.rejection_reason = reason
    application.reviewed_by = reviewed_by
    application.reviewed_at = timezone.now()
    application.save(update_fields=['status', 'rejection_reason', 'reviewed_by', 'reviewed_at', 'updated_at'])
    _notify_application_status(application)
    return application


def withdraw_rental_application(application, *, tenant):
    from .models import RentalApplication
    if application.tenant_id != tenant.id:
        raise ValueError("You can only withdraw your own application.")
    if application.status != RentalApplication.Status.PENDING:
        raise ValueError("Only a pending application can be withdrawn.")
    application.status = RentalApplication.Status.WITHDRAWN
    application.save(update_fields=['status', 'updated_at'])
    return application


def _notify_application_status(application):
    try:
        from apps.notifications.services import notify_user
        from .models import RentalApplication
        messages = {
            RentalApplication.Status.APPROVED: (
                "Application Approved", f"Your application for {application.unit} has been approved - your lease is now active."
            ),
            RentalApplication.Status.REJECTED: (
                "Application Update", f"Your application for {application.unit} was not successful."
                + (f" Reason: {application.rejection_reason}" if application.rejection_reason else "")
            ),
        }
        title, message = messages.get(application.status, (None, None))
        if title:
            notify_user(application.tenant, title=title, message=message, notification_type="application")
    except Exception as e:
        logger.error("Notification dispatch failed: %s", e)
