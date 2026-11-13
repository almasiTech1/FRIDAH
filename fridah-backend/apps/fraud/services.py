import logging
from django.utils import timezone

logger = logging.getLogger('apps.fraud')

DUPLICATE_LISTING_RADIUS_DEGREES = 0.0005  # roughly ~50m at the equator, close enough for Kenya's latitude


def detect_duplicate_listings():
    """
    Flags properties from *different* landlords sitting at essentially the same
    coordinates - a common pattern for stolen/copied listings (fraudster re-lists a
    real property they don't own, using photos/details scraped from the original).
    Same-landlord duplicates (e.g. re-submitting after a rejection) are not flagged.
    """
    from apps.properties.models import Property
    from .models import FraudFlag

    created = 0
    properties = list(
        Property.objects.filter(
            status=Property.Status.ACTIVE, latitude__isnull=False, longitude__isnull=False
        ).only('id', 'landlord_id', 'name', 'latitude', 'longitude')
    )

    seen_pairs = set()
    for i, p1 in enumerate(properties):
        for p2 in properties[i + 1:]:
            if p1.landlord_id == p2.landlord_id:
                continue
            if abs(p1.latitude - p2.latitude) > DUPLICATE_LISTING_RADIUS_DEGREES:
                continue
            if abs(p1.longitude - p2.longitude) > DUPLICATE_LISTING_RADIUS_DEGREES:
                continue

            pair_key = tuple(sorted([str(p1.id), str(p2.id)]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            already_flagged = FraudFlag.objects.filter(
                flag_type=FraudFlag.FlagType.DUPLICATE_LISTING,
                subject_type='property', subject_id=str(p1.id),
                evidence__matched_property_id=str(p2.id),
            ).exists()
            if already_flagged:
                continue

            FraudFlag.objects.create(
                flag_type=FraudFlag.FlagType.DUPLICATE_LISTING,
                subject_type='property', subject_id=str(p1.id),
                reason=(
                    f'"{p1.name}" and "{p2.name}" are listed at nearly identical coordinates '
                    f'by different landlords - possible duplicate/stolen listing.'
                ),
                evidence={
                    'matched_property_id': str(p2.id), 'matched_property_name': p2.name,
                    'landlord_1': str(p1.landlord_id), 'landlord_2': str(p2.landlord_id),
                },
            )
            created += 1

    logger.info("Duplicate listing detection: %d new flags.", created)
    return created


def detect_suspicious_payment_patterns(window_hours=24, failure_threshold=5):
    """
    Flags phone numbers with an unusually high number of failed M-Pesa attempts in a
    short window - could indicate a stolen/invalid number being used repeatedly, or
    an attacker probing for a valid STK push target.
    """
    from django.db.models import Count
    from apps.payments.models import MpesaTransaction
    from .models import FraudFlag

    since = timezone.now() - timezone.timedelta(hours=window_hours)
    suspicious = (
        MpesaTransaction.objects.filter(created_at__gte=since)
        .exclude(result_code=0)
        .values('phone_number')
        .annotate(failure_count=Count('id'))
        .filter(failure_count__gte=failure_threshold, phone_number__isnull=False)
        .exclude(phone_number='')
    )

    created = 0
    for row in suspicious:
        phone = row['phone_number']
        already_flagged = FraudFlag.objects.filter(
            flag_type=FraudFlag.FlagType.SUSPICIOUS_PAYMENT_PATTERN,
            subject_type='phone', subject_id=phone,
            created_at__gte=since,
        ).exists()
        if already_flagged:
            continue

        FraudFlag.objects.create(
            flag_type=FraudFlag.FlagType.SUSPICIOUS_PAYMENT_PATTERN,
            subject_type='phone', subject_id=phone,
            reason=f"{row['failure_count']} failed M-Pesa attempts from {phone} in the last {window_hours}h.",
            evidence={'failure_count': row['failure_count'], 'window_hours': window_hours},
        )
        created += 1

    logger.info("Suspicious payment pattern detection: %d new flags.", created)
    return created


def detect_abnormal_pricing(low_ratio=0.4, high_ratio=2.5):
    """
    Flags units priced far outside the range of real comparable units in the same
    area/bedroom count - reuses the same grounded comparable logic as the AI rent
    estimator. Suspiciously cheap listings are a classic deposit-scam lure; wildly
    overpriced ones are usually just data-entry errors, but worth a look either way.
    """
    from apps.properties.models import Unit
    from apps.ai.rent_estimator import get_comparable_units
    from .models import FraudFlag
    import statistics

    created = 0
    checked_area_bedroom_pairs = set()

    for unit in Unit.objects.filter(status=Unit.Status.VACANT).select_related('property'):
        key = (unit.property.county, unit.property.town, unit.bedrooms)
        if key in checked_area_bedroom_pairs:
            pass  # still check this specific unit, just reuse the comparable set if we had cached it
        checked_area_bedroom_pairs.add(key)

        comparables = get_comparable_units(unit.property.county, unit.property.town, unit.bedrooms, exclude_unit_id=unit.id)
        rents = [float(u.rent_amount) for u in comparables if u.rent_amount]
        if len(rents) < 3:
            continue  # not enough data to judge "abnormal" confidently

        median = statistics.median(rents)
        rent = float(unit.rent_amount)
        if median <= 0:
            continue

        ratio = rent / median
        if low_ratio <= ratio <= high_ratio:
            continue

        already_flagged = FraudFlag.objects.filter(
            flag_type=FraudFlag.FlagType.ABNORMAL_PRICING, subject_type='unit', subject_id=str(unit.id),
            status=FraudFlag.Status.OPEN,
        ).exists()
        if already_flagged:
            continue

        direction = "far below" if ratio < low_ratio else "far above"
        FraudFlag.objects.create(
            flag_type=FraudFlag.FlagType.ABNORMAL_PRICING, subject_type='unit', subject_id=str(unit.id),
            reason=(
                f"Unit rent KES {rent:,.0f} is {direction} the area median of KES {median:,.0f} "
                f"({len(rents)} comparables) for {unit.bedrooms}-bedroom units in {unit.property.town}."
            ),
            evidence={'unit_rent': rent, 'area_median': median, 'comparable_count': len(rents), 'ratio': round(ratio, 2)},
        )
        created += 1

    logger.info("Abnormal pricing detection: %d new flags.", created)
    return created


def detect_multi_account_national_id():
    """Flags multiple user accounts registered with the same national ID number."""
    from django.db.models import Count
    from apps.users.models import User
    from .models import FraudFlag

    duplicates = (
        User.objects.exclude(national_id__isnull=True).exclude(national_id='')
        .values('national_id')
        .annotate(account_count=Count('id'))
        .filter(account_count__gte=2)
    )

    created = 0
    for row in duplicates:
        national_id = row['national_id']
        already_flagged = FraudFlag.objects.filter(
            flag_type=FraudFlag.FlagType.MULTI_ACCOUNT_PHONE, subject_type='national_id', subject_id=national_id,
            status=FraudFlag.Status.OPEN,
        ).exists()
        if already_flagged:
            continue

        user_ids = list(User.objects.filter(national_id=national_id).values_list('id', flat=True))
        FraudFlag.objects.create(
            flag_type=FraudFlag.FlagType.MULTI_ACCOUNT_PHONE, subject_type='national_id', subject_id=national_id,
            reason=f"{row['account_count']} accounts registered with the same national ID.",
            evidence={'user_ids': [str(u) for u in user_ids], 'account_count': row['account_count']},
        )
        created += 1

    logger.info("Multi-account detection: %d new flags.", created)
    return created


def run_all_detections():
    return {
        'duplicate_listings': detect_duplicate_listings(),
        'suspicious_payments': detect_suspicious_payment_patterns(),
        'abnormal_pricing': detect_abnormal_pricing(),
        'multi_account': detect_multi_account_national_id(),
    }
