from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Avg, Count, Q
from apps.users.views import success
from apps.properties.models import Property, Unit
from apps.rentals.models import Lease, Invoice
from apps.users.permissions import IsLandlordOrAdmin


class VacancyAnalyticsView(APIView):
    permission_classes = [IsLandlordOrAdmin]

    def get(self, request):
        user = request.user
        props = Property.objects.filter(landlord=user)
        result = []
        for prop in props:
            units = prop.units.all()
            vacant = units.filter(status='vacant')
            occupied = units.filter(status='occupied')
            avg_rent = units.aggregate(avg=Avg('rent_amount'))['avg'] or 0
            result.append({
                'property_id': str(prop.id),
                'property_name': prop.name,
                'total_units': units.count(),
                'occupied': occupied.count(),
                'vacant': vacant.count(),
                'occupancy_rate': round(occupied.count() / units.count() * 100, 1) if units.count() else 0,
                'avg_rent': float(avg_rent),
                'monthly_potential': float(avg_rent * units.count()),
                'monthly_actual': float(avg_rent * occupied.count()),
                'revenue_gap': float(avg_rent * vacant.count()),
            })
        summary = {
            'total_properties': len(result),
            'total_units': sum(r['total_units'] for r in result),
            'total_occupied': sum(r['occupied'] for r in result),
            'total_vacant': sum(r['vacant'] for r in result),
            'overall_occupancy_rate': round(sum(r['occupied'] for r in result) / max(sum(r['total_units'] for r in result), 1) * 100, 1),
            'total_monthly_potential': sum(r['monthly_potential'] for r in result),
            'total_monthly_actual': sum(r['monthly_actual'] for r in result),
            'total_revenue_gap': sum(r['revenue_gap'] for r in result),
        }
        return success({'properties': result, 'summary': summary})


class MarketBenchmarkView(APIView):
    """Compare a landlord's rents against the platform average for same county/town."""

    def get(self, request):
        county = request.query_params.get('county')
        town = request.query_params.get('town')
        property_type = request.query_params.get('property_type')

        qs = Unit.objects.filter(property__status='active')
        if county:
            qs = qs.filter(property__county__icontains=county)
        if town:
            qs = qs.filter(property__town__icontains=town)
        if property_type:
            qs = qs.filter(property__property_type=property_type)

        market = qs.aggregate(
            avg_rent=Avg('rent_amount'),
            min_rent=Avg('rent_amount'),
            total_listings=Count('id'),
        )

        # User's own units for comparison
        my_units = Unit.objects.filter(property__landlord=request.user)
        if county:
            my_units = my_units.filter(property__county__icontains=county)
        if town:
            my_units = my_units.filter(property__town__icontains=town)
        my_avg = my_units.aggregate(avg=Avg('rent_amount'))['avg']

        data = {
            'market': {
                'county': county, 'town': town, 'property_type': property_type,
                'avg_rent': round(float(market['avg_rent'] or 0), 2),
                'total_listings': market['total_listings'],
            },
            'your_avg_rent': round(float(my_avg or 0), 2),
            'vs_market': round(float((my_avg or 0) - (market['avg_rent'] or 0)), 2),
            'insight': _benchmark_insight(my_avg, market['avg_rent']),
        }
        return success(data)


def _benchmark_insight(my_avg, market_avg):
    if not my_avg or not market_avg:
        return "Not enough data for comparison."
    pct = ((my_avg - market_avg) / market_avg) * 100
    if pct > 15:
        return f"Your rents are {abs(pct):.0f}% above market average. Consider if this is justified by amenities."
    elif pct < -15:
        return f"Your rents are {abs(pct):.0f}% below market average. You may be able to increase by KES {market_avg - my_avg:,.0f}/month."
    else:
        return "Your rents are well-aligned with the local market average."


class RentForecastView(APIView):
    permission_classes = [IsLandlordOrAdmin]

    def get(self, request):
        from apps.rentals.models import Lease
        from datetime import date
        from dateutil.relativedelta import relativedelta
        active_leases = Lease.objects.filter(landlord=request.user, status='active')
        today = date.today()
        forecast = []
        for i in range(12):
            month = today + relativedelta(months=i)
            expected = sum(l.rent_amount for l in active_leases if not l.end_date or l.end_date >= month)
            forecast.append({
                'month': month.strftime('%b %Y'),
                'expected_revenue': float(expected),
                'active_leases': active_leases.filter(
                    Q(end_date__isnull=True) | Q(end_date__gte=month)
                ).count(),
            })
        return success({'forecast': forecast, 'total_12_months': sum(f['expected_revenue'] for f in forecast)})


class BulkInvoiceGenerationView(APIView):
    """Landlord generates invoices for all active leases in one click."""
    permission_classes = [IsLandlordOrAdmin]

    def post(self, request):
        from apps.rentals.models import Lease, Invoice
        from datetime import date
        from dateutil.relativedelta import relativedelta
        import uuid

        today = date.today()
        period_start = today.replace(day=1)
        period_end = (period_start + relativedelta(months=1)) - relativedelta(days=1)

        prop_id = request.data.get('property_id')
        leases = Lease.objects.filter(landlord=request.user, status='active')
        if prop_id:
            leases = leases.filter(unit__property_id=prop_id)

        created = []
        skipped = []
        for lease in leases:
            exists = Invoice.objects.filter(lease=lease, period_start=period_start, invoice_type='rent').exists()
            if exists:
                skipped.append(str(lease.id))
                continue
            due_date = period_start.replace(day=min(lease.rent_due_day, 28))
            inv = Invoice.objects.create(
                lease=lease, tenant=lease.tenant, invoice_type='rent',
                amount=lease.rent_amount, period_start=period_start,
                period_end=period_end, due_date=due_date,
            )
            # Notify tenant
            try:
                from apps.notifications.services import notify_user
                notify_user(lease.tenant, title="New Invoice", message=f"Your rent invoice of KES {lease.rent_amount:,.0f} for {period_start.strftime('%B %Y')} is ready.", notification_type="payment", send_sms_too=True)
            except Exception:
                pass
            created.append(inv.invoice_number)

        return success(
            {'created': len(created), 'skipped': len(skipped), 'invoice_numbers': created},
            message=f"Generated {len(created)} invoice(s). {len(skipped)} already existed."
        )


class MaintenanceAnalyticsView(APIView):
    """
    Maintenance response time, cost, and category/priority breakdown - the piece
    flagged as missing in the AI/Analytics architecture review: MaintenanceRequest,
    ServiceJob and Quote all had the underlying data, but nothing aggregated it.

    Scoped via properties_visible_to() rather than Property.objects.filter(landlord=user)
    like the older analytics views, so it works for agency staff (Property Manager,
    Caretaker) as well as landlords/admins - one of the concrete fixes recommended
    in the architecture review, applied here since this is a new endpoint rather
    than a change to an existing one's contract.
    """
    def get(self, request):
        from apps.agencies.permissions import properties_visible_to
        from apps.rentals.models import MaintenanceRequest
        from apps.services.models import Quote

        properties = properties_visible_to(request.user)
        requests_qs = MaintenanceRequest.objects.filter(unit__property__in=properties)

        total = requests_qs.count()
        by_status = dict(requests_qs.values_list('status').annotate(c=Count('id')).values_list('status', 'c'))
        by_priority = dict(requests_qs.values_list('priority').annotate(c=Count('id')).values_list('priority', 'c'))
        by_category = list(
            requests_qs.values('category').annotate(count=Count('id')).order_by('-count')[:10]
        )

        resolved = requests_qs.filter(resolved_at__isnull=False)
        response_times_hours = [
            (r.resolved_at - r.created_at).total_seconds() / 3600
            for r in resolved.only('created_at', 'resolved_at')
        ]
        avg_response_hours = round(sum(response_times_hours) / len(response_times_hours), 1) if response_times_hours else None

        accepted_quotes = Quote.objects.filter(
            status=Quote.Status.ACCEPTED,
            job__maintenance_request__in=requests_qs,
        )
        avg_cost = accepted_quotes.aggregate(avg=Avg('amount'))['avg']
        from django.db.models import Sum
        total_cost = accepted_quotes.aggregate(total=Sum('amount'))['total']

        open_statuses = [MaintenanceRequest.Status.OPEN, MaintenanceRequest.Status.ASSIGNED, MaintenanceRequest.Status.IN_PROGRESS]

        return success({
            'total_requests': total,
            'open_requests': requests_qs.filter(status__in=open_statuses).count(),
            'by_status': by_status,
            'by_priority': by_priority,
            'top_categories': by_category,
            'avg_response_time_hours': avg_response_hours,
            'avg_cost_per_job': str(avg_cost.quantize(Decimal('0.01'))) if avg_cost else None,
            'total_cost_this_scope': str(total_cost) if total_cost else '0',
            'jobs_with_accepted_quote': accepted_quotes.count(),
        })


class LeasingFunnelAnalyticsView(APIView):
    """
    Leasing conversion funnel - flagged as missing in the AI/Analytics architecture
    review (relevant to the Leasing Agent role, which has property.view + tenants.view
    + listings.manage permissions but no funnel view of its own work).

    Honest limitation: the platform doesn't currently have first-class "viewing
    scheduled" or "formal rental application" models - a tenant expresses interest
    by saving a property (SavedProperty) and a lease is either created directly by
    a landlord/agent or via some off-platform process, then activated. So this is a
    3-stage proxy funnel (saved -> lease created -> lease active), not the full
    4-stage search->viewing->application->signed funnel described in the review.
    Adding real viewing/application tracking would need new models - a bigger,
    deliberate addition rather than something to bolt on here.
    """
    def get(self, request):
        from datetime import timedelta
        from django.utils import timezone
        from apps.agencies.permissions import properties_visible_to
        from apps.properties.models import SavedProperty
        from apps.rentals.models import Lease

        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)
        properties = properties_visible_to(request.user)

        saves = SavedProperty.objects.filter(property__in=properties, created_at__gte=since)
        leases_created = Lease.objects.filter(unit__property__in=properties, created_at__gte=since)
        leases_activated = leases_created.filter(status=Lease.Status.ACTIVE)

        saved_property_count = saves.values('property').distinct().count()
        properties_with_lease = leases_created.values('unit__property').distinct().count()

        per_property = []
        for prop in properties.filter(id__in=saves.values('property')).distinct()[:20]:
            prop_saves = saves.filter(property=prop).count()
            prop_leases = leases_created.filter(unit__property=prop).count()
            per_property.append({
                'property_id': str(prop.id),
                'property_name': prop.name,
                'saves': prop_saves,
                'leases_created': prop_leases,
                'save_to_lease_rate': round(prop_leases / prop_saves * 100, 1) if prop_saves else 0,
            })

        return success({
            'period_days': days,
            'funnel': {
                'properties_saved': saved_property_count,
                'total_saves': saves.count(),
                'leases_created': leases_created.count(),
                'leases_activated': leases_activated.count(),
                'properties_with_at_least_one_lease': properties_with_lease,
            },
            'conversion_rates': {
                'save_to_lease_created_pct': (
                    round(leases_created.count() / saves.count() * 100, 1) if saves.count() else 0
                ),
                'lease_created_to_active_pct': (
                    round(leases_activated.count() / leases_created.count() * 100, 1) if leases_created.count() else 0
                ),
            },
            'top_properties_by_saves': per_property,
        })


class RevenueForecastView(APIView):
    """
    Predictive revenue forecast - distinct from RentForecastView above (which
    simply sums active-lease rent as "expected revenue" with an implicit 100%
    collection assumption). This one factors in the property's own actual
    historical collection rate (collected vs billed, from real Invoice data over
    the trailing period), so a portfolio with chronic arrears gets a materially
    different, more honest forecast than one that always collects on time -
    flagged as a missing capability ("predictive vacancy analytics / revenue
    forecasting") in the architecture review and the project README.

    Agency-aware via properties_visible_to() since this is a new endpoint (see
    the note on RentForecastView/VacancyAnalyticsView about not silently
    changing existing endpoints' contracts).
    """
    def get(self, request):
        from datetime import date
        from dateutil.relativedelta import relativedelta
        from django.db.models import Sum
        from django.utils import timezone
        from apps.agencies.permissions import properties_visible_to
        from apps.rentals.models import Lease, Invoice

        properties = properties_visible_to(request.user)
        lookback_months = int(request.query_params.get('lookback_months', 6))
        forecast_months = int(request.query_params.get('forecast_months', 6))

        lookback_start = timezone.now().date() - relativedelta(months=lookback_months)
        historical = Invoice.objects.filter(
            lease__unit__property__in=properties, invoice_type=Invoice.InvoiceType.RENT,
            due_date__gte=lookback_start, due_date__lte=timezone.now().date(),
        )
        billed = historical.aggregate(total=Sum('amount'))['total'] or 0
        collected = historical.aggregate(total=Sum('amount_paid'))['total'] or 0
        collection_rate = float(collected) / float(billed) if billed else 1.0

        active_leases = Lease.objects.filter(unit__property__in=properties, status=Lease.Status.ACTIVE)
        today = date.today()
        forecast = []
        for i in range(forecast_months):
            month = today + relativedelta(months=i)
            leases_this_month = active_leases.filter(Q(end_date__isnull=True) | Q(end_date__gte=month))
            billed_this_month = sum(l.rent_amount for l in leases_this_month)
            forecast.append({
                'month': month.strftime('%b %Y'),
                'billed_revenue': float(billed_this_month),
                'expected_collected_revenue': round(float(billed_this_month) * collection_rate, 2),
                'active_leases': leases_this_month.count(),
                'leases_expiring_before_this_month': active_leases.filter(
                    end_date__isnull=False, end_date__lt=month,
                ).count(),
            })

        return success({
            'historical_collection_rate_pct': round(collection_rate * 100, 1),
            'historical_period': {'lookback_months': lookback_months, 'billed': str(billed), 'collected': str(collected)},
            'forecast': forecast,
            'total_expected_collected': round(sum(f['expected_collected_revenue'] for f in forecast), 2),
        })
