import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger('apps.rentals')


def _default_renewal_terms(lease):
    """Like-for-like extension of the same length as the current term, landlord can edit before it's sent."""
    from dateutil.relativedelta import relativedelta

    term_length = relativedelta(lease.end_date, lease.start_date)
    proposed_start = lease.end_date + timezone.timedelta(days=1)
    proposed_end = proposed_start + term_length
    return proposed_start, proposed_end


@shared_task
def check_lease_renewals():
    """
    Run daily via Celery Beat. For every active lease with a fixed end_date, ensures a
    LeaseRenewal offer exists once we're within 60 days of expiry, and notifies the
    tenant at the 60-day and 30-day marks (once each).
    """
    from .models import Lease, LeaseRenewal
    from apps.notifications.services import notify_user

    today = timezone.now().date()
    notified_60, notified_30, created = 0, 0, 0

    leases = Lease.objects.filter(status=Lease.Status.ACTIVE, end_date__isnull=False)
    for lease in leases:
        days_to_expiry = (lease.end_date - today).days
        if days_to_expiry < 0 or days_to_expiry > 60:
            continue

        proposed_start, proposed_end = _default_renewal_terms(lease)
        renewal, was_created = LeaseRenewal.objects.get_or_create(
            lease=lease,
            defaults=dict(
                proposed_start_date=proposed_start,
                proposed_end_date=proposed_end,
                proposed_rent_amount=lease.rent_amount,
            ),
        )
        if was_created:
            created += 1

        if renewal.status != LeaseRenewal.Status.PENDING:
            continue

        if days_to_expiry <= 60 and not renewal.notified_60_day_at:
            notify_user(
                lease.tenant,
                title="Lease Renewal Available",
                message=(
                    f"Your lease for {lease.unit} ends on {lease.end_date}. "
                    f"A renewal offer is ready for you to review in the app."
                ),
                notification_type="lease",
                send_sms_too=True,
            )
            renewal.notified_60_day_at = timezone.now()
            renewal.save(update_fields=['notified_60_day_at'])
            notified_60 += 1

        if days_to_expiry <= 30 and not renewal.notified_30_day_at:
            notify_user(
                lease.tenant,
                title="Lease Renewal Reminder",
                message=(
                    f"Only {days_to_expiry} days left on your lease for {lease.unit}. "
                    f"Accept or decline your renewal offer in the app to avoid a gap."
                ),
                notification_type="lease",
                send_sms_too=True,
            )
            renewal.notified_30_day_at = timezone.now()
            renewal.save(update_fields=['notified_30_day_at'])
            notified_30 += 1

    logger.info(
        "Lease renewal check: %d offers created, %d 60-day notices, %d 30-day notices.",
        created, notified_60, notified_30,
    )
    return {'created': created, 'notified_60_day': notified_60, 'notified_30_day': notified_30}


@shared_task
def expire_stale_lease_renewals():
    """Run daily: marks renewal offers EXPIRED once the underlying lease has already ended with no response."""
    from .models import Lease, LeaseRenewal

    today = timezone.now().date()
    stale = LeaseRenewal.objects.filter(status=LeaseRenewal.Status.PENDING, lease__end_date__lt=today)
    count = stale.update(status=LeaseRenewal.Status.EXPIRED)
    logger.info("Expired %d stale lease renewal offers.", count)
    return count


@shared_task
def generate_flat_fee_utility_invoices_task():
    from .services import generate_flat_fee_utility_invoices
    return generate_flat_fee_utility_invoices()


@shared_task
def generate_amenity_invoices_task():
    from .amenities import generate_all
    return generate_all()
