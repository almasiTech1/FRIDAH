"""
Shared per-property financial calculations.

These were previously defined only inside apps/agencies/services.py (for owner
statements) while apps/analytics/advanced_views.py computed a differently-shaped
"revenue gap" metric independently for the landlord vacancy dashboard. The two
were never reconciled and would have kept drifting apart as each app evolved.

This module is the single source of truth for the *precise, period-scoped*
versions of these calculations (real per-unit rent, prorated across an exact
date range) - used anywhere that needs to reconcile actual money, like owner
statements and the agency rollup dashboard.

Note: apps.analytics.advanced_views.VacancyAnalyticsView intentionally keeps its
own simpler "monthly snapshot using average rent across all units" metric as-is
- it answers a different question (a live estimate for a dashboard, not a
period-exact reconciliation) and changing its output would be an API contract
change for the existing landlord dashboard. New features should call the
functions here rather than write a third variant.
"""
from decimal import Decimal

from django.db.models import Sum


def collected_rent_for_period(property, period_start, period_end):
    """Sum of completed rent payments for a property's leases within [period_start, period_end]."""
    from apps.payments.models import Payment
    total = Payment.objects.filter(
        status=Payment.Status.COMPLETED,
        invoice__lease__unit__property=property,
        invoice__invoice_type='rent',
        completed_at__date__gte=period_start,
        completed_at__date__lte=period_end,
    ).aggregate(total=Sum('amount'))['total']
    return total or Decimal('0')


def arrears_for_property(property, as_of_date):
    """Outstanding rent/other invoice balance for a property as of a given date."""
    from apps.rentals.models import Invoice
    total = Invoice.objects.filter(
        lease__unit__property=property, due_date__lte=as_of_date,
        status__in=[Invoice.Status.PENDING, Invoice.Status.PARTIALLY_PAID, Invoice.Status.OVERDUE],
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    paid = Invoice.objects.filter(
        lease__unit__property=property, due_date__lte=as_of_date,
        status__in=[Invoice.Status.PENDING, Invoice.Status.PARTIALLY_PAID, Invoice.Status.OVERDUE],
    ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0')
    return max(total - paid, Decimal('0'))


def vacancy_loss_for_period(property, period_start, period_end):
    """Estimated rent lost to vacancy: each currently-vacant unit's daily rent
    rate, prorated across the exact number of days in the period."""
    from apps.properties.models import Unit
    days = (period_end - period_start).days + 1
    vacant_units = Unit.objects.filter(property=property, status=Unit.Status.VACANT)
    daily_rate_sum = sum((u.rent_amount / 30) for u in vacant_units) if vacant_units.exists() else Decimal('0')
    return (Decimal(daily_rate_sum) * days).quantize(Decimal('0.01'))


def collected_booking_revenue_for_period(listing, period_start, period_end):
    """
    Sum of amount actually paid on bookings for a listing whose stay checked out
    within [period_start, period_end]. Revenue is recognised on checkout (once the
    stay has actually happened) rather than on booking date, so a booking made in
    one month for a stay next month doesn't inflate this month's statement.
    """
    from apps.bookings.models import Booking
    total = Booking.objects.filter(
        listing=listing,
        status__in=[Booking.Status.CHECKED_OUT, Booking.Status.CHECKED_IN],
        check_out_date__gte=period_start, check_out_date__lte=period_end,
    ).aggregate(total=Sum('amount_paid'))['total']
    return total or Decimal('0')


def occupancy_for_period(listing, period_start, period_end):
    """Room-nights actually occupied vs. room-nights available for a listing/period."""
    from apps.bookings.models import Booking, RoomType
    days = (period_end - period_start).days + 1
    total_rooms = RoomType.objects.filter(listing=listing).aggregate(total=Sum('total_rooms'))['total'] or 0
    available_room_nights = total_rooms * days
    if available_room_nights == 0:
        return Decimal('0')
    bookings = Booking.objects.filter(
        listing=listing, status__in=[Booking.Status.CHECKED_OUT, Booking.Status.CHECKED_IN, Booking.Status.CONFIRMED],
        check_in_date__lte=period_end, check_out_date__gte=period_start,
    )
    occupied_room_nights = 0
    for b in bookings:
        overlap_start = max(b.check_in_date, period_start)
        overlap_end = min(b.check_out_date, period_end)
        nights = max((overlap_end - overlap_start).days, 0)
        occupied_room_nights += nights * b.num_rooms
    return (Decimal(occupied_room_nights) / Decimal(available_room_nights) * 100).quantize(Decimal('0.01'))


def monthly_totals(queryset, date_field, value_field='amount', months=12):
    """
    Sum of `value_field` per calendar month for the last `months` months (oldest first, the
    current month last). Months with no activity are returned as 0 so charts have no gaps.
    One grouped database query; amounts are returned as plain floats for JSON.
    """
    from django.db.models import Sum
    from django.db.models.functions import TruncMonth
    from django.utils import timezone

    now = timezone.localtime()
    first = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    keys = []
    y, m = first.year, first.month
    for _ in range(months):
        keys.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    keys.reverse()
    start = first.replace(year=keys[0][0], month=keys[0][1])
    rows = (queryset.filter(**{f'{date_field}__gte': start})
            .annotate(_m=TruncMonth(date_field))
            .values('_m').annotate(total=Sum(value_field)))
    by_month = {(r['_m'].year, r['_m'].month): float(r['total'] or 0) for r in rows if r['_m']}
    return [{'month': f'{y}-{m:02d}', 'amount': by_month.get((y, m), 0.0)} for y, m in keys]
