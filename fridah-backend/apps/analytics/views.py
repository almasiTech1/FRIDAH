from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Count, Q
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response

from apps.users.permissions import IsAdminRole
from apps.properties.models import Property, Unit
from apps.rentals.models import Lease, Invoice, MaintenanceRequest
from apps.bookings.models import Listing, Booking
from apps.services.models import ServiceJob, Quote
from apps.payments.models import Payment, Payout, WalletTransaction
from apps.payments.services import get_wallet_balance
from apps.users.models import User
from common.calculations import monthly_totals  # noqa: F401  (re-exported for existing imports)


def success(data=None, message="OK", status_code=status.HTTP_200_OK):
    return Response({'success': True, 'message': message, 'data': data}, status=status_code)


class TenantDashboardView(APIView):
    def get(self, request):
        user = request.user
        leases = Lease.objects.filter(tenant=user)
        active_lease = leases.filter(status=Lease.Status.ACTIVE).first()
        invoices = Invoice.objects.filter(tenant=user)
        pending_invoices = invoices.filter(status__in=[Invoice.Status.PENDING, Invoice.Status.OVERDUE, Invoice.Status.PARTIALLY_PAID])
        maintenance = MaintenanceRequest.objects.filter(tenant=user)

        data = {
            'active_lease_id': str(active_lease.id) if active_lease else None,
            'rent_amount': active_lease.rent_amount if active_lease else None,
            'pending_invoices_count': pending_invoices.count(),
            'pending_balance': pending_invoices.aggregate(total=Sum('amount'))['total'] or 0,
            'open_maintenance_requests': maintenance.filter(status__in=['open', 'assigned', 'in_progress']).count(),
            'total_paid_this_year': Payment.objects.filter(
                payer=user, status=Payment.Status.COMPLETED, created_at__year=timezone.now().year
            ).aggregate(total=Sum('amount'))['total'] or 0,
        }
        return success(data)


class LandlordDashboardView(APIView):
    def get(self, request):
        user = request.user
        properties = Property.objects.filter(landlord=user)
        units = Unit.objects.filter(property__landlord=user)
        leases = Lease.objects.filter(landlord=user, status=Lease.Status.ACTIVE)
        invoices = Invoice.objects.filter(lease__landlord=user)
        overdue = invoices.filter(status=Invoice.Status.OVERDUE)
        maintenance = MaintenanceRequest.objects.filter(unit__property__landlord=user)
        # One definition of "collected" for both the headline tile and the chart: completed payments
        # on this landlord's leases, counted in the month they completed (partial payments included).
        collected_by_month = monthly_totals(
            Payment.objects.filter(invoice__lease__landlord=user, status=Payment.Status.COMPLETED), 'completed_at',
        )

        data = {
            'total_properties': properties.count(),
            'total_units': units.count(),
            'occupied_units': units.filter(status=Unit.Status.OCCUPIED).count(),
            'vacant_units': units.filter(status=Unit.Status.VACANT).count(),
            'active_leases': leases.count(),
            'overdue_invoices_count': overdue.count(),
            'overdue_amount': overdue.aggregate(total=Sum('amount'))['total'] or 0,
            'collected_this_month': collected_by_month[-1]['amount'],
            'open_maintenance_requests': maintenance.exclude(status__in=['resolved', 'closed']).count(),
            'wallet_balance': get_wallet_balance(user),
            # Real month-by-month history (completed payments on this landlord's leases), oldest first.
            'collected_by_month': collected_by_month,
        }
        return success(data)


class ServiceProviderDashboardView(APIView):
    def get(self, request):
        user = request.user
        jobs = ServiceJob.objects.filter(assigned_provider=user)
        quotes = Quote.objects.filter(provider=user)

        data = {
            'active_jobs': jobs.filter(status__in=['assigned', 'in_progress']).count(),
            'completed_jobs': jobs.filter(status='completed').count(),
            'pending_quotes': quotes.filter(status='pending').count(),
            'accepted_quotes': quotes.filter(status='accepted').count(),
            'wallet_balance': get_wallet_balance(user),
            'available_open_jobs': ServiceJob.objects.filter(status='open').count(),
            # Money credited to the provider's wallet each month (earnings after commission), oldest first.
            'earnings_by_month': monthly_totals(
                WalletTransaction.objects.filter(user=user, entry_type=WalletTransaction.EntryType.CREDIT), 'created_at',
            ),
        }
        return success(data)


class HotelOwnerDashboardView(APIView):
    def get(self, request):
        user = request.user
        listings = Listing.objects.filter(host=user)
        bookings = Booking.objects.filter(host=user)
        today = timezone.now().date()

        data = {
            'total_listings': listings.count(),
            'active_listings': listings.filter(status='active').count(),
            'upcoming_checkins': bookings.filter(check_in_date=today, status='confirmed').count(),
            'current_guests': bookings.filter(status='checked_in').count(),
            'total_bookings_this_month': bookings.filter(
                created_at__month=today.month, created_at__year=today.year
            ).count(),
            'revenue_this_month': Payment.objects.filter(
                booking__host=user, status=Payment.Status.COMPLETED,
                completed_at__month=today.month, completed_at__year=today.year
            ).aggregate(total=Sum('amount'))['total'] or 0,
            'wallet_balance': get_wallet_balance(user),
            'revenue_by_month': monthly_totals(
                Payment.objects.filter(booking__host=user, status=Payment.Status.COMPLETED), 'completed_at',
            ),
        }
        return success(data)


class AdminDashboardView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        today = timezone.now().date()
        data = {
            'total_users': User.objects.count(),
            'users_by_role': dict(User.objects.values_list('role').annotate(c=Count('id'))),
            'total_properties': Property.objects.count(),
            'total_listings': Listing.objects.count(),
            'pending_property_approvals': Property.objects.filter(status='pending_approval').count(),
            'pending_listing_approvals': Listing.objects.filter(status='pending_approval').count(),
            'pending_kyc': User.objects.filter(kyc_status='pending').count(),
            'active_leases': Lease.objects.filter(status='active').count(),
            'active_bookings': Booking.objects.filter(status__in=['confirmed', 'checked_in']).count(),
            'total_revenue_this_month': Payment.objects.filter(
                status='completed', completed_at__month=today.month, completed_at__year=today.year
            ).aggregate(total=Sum('amount'))['total'] or 0,
            'total_payouts_this_month': Payout.objects.filter(
                status='completed', completed_at__month=today.month, completed_at__year=today.year
            ).aggregate(total=Sum('amount'))['total'] or 0,
            'open_maintenance_requests': MaintenanceRequest.objects.exclude(status__in=['resolved', 'closed']).count(),
            'new_signups_this_month': User.objects.filter(
                created_at__month=today.month, created_at__year=today.year
            ).count(),
            'revenue_by_month': monthly_totals(Payment.objects.filter(status=Payment.Status.COMPLETED), 'completed_at'),
            'payouts_by_month': monthly_totals(Payout.objects.filter(status='completed'), 'completed_at'),
        }
        return success(data)


class AdminPortfolioView(APIView):
    """
    Platform-wide portfolio overview for administrators, filterable by county, property
    type, landlord, managing agency and billing date range. Aggregated in the database
    (no per-row Python loops) so it stays usable as the portfolio grows.
    """
    permission_classes = [IsAdminRole]

    def get(self, request):
        from datetime import timedelta
        from django.db.models import F, Q
        from apps.properties.models import Unit
        from apps.rentals.models import Invoice

        qp = request.query_params
        props = Property.objects.all()
        if qp.get('county'):
            props = props.filter(county__iexact=qp['county'])
        if qp.get('property_type'):
            props = props.filter(property_type=qp['property_type'])
        if qp.get('landlord'):
            props = props.filter(landlord_id=qp['landlord'])
        if qp.get('agency'):
            props = props.filter(management_assignments__agency_id=qp['agency'],
                                 management_assignments__status='active').distinct()

        units = Unit.objects.filter(property__in=props)
        total_units = units.count()
        occupied = units.filter(status='occupied').count()

        invoices = Invoice.objects.filter(lease__unit__property__in=props).exclude(status='cancelled')
        if qp.get('date_from'):
            invoices = invoices.filter(due_date__gte=qp['date_from'])
        if qp.get('date_to'):
            invoices = invoices.filter(due_date__lte=qp['date_to'])
        totals = invoices.aggregate(billed=Sum('amount'), collected=Sum('amount_paid'))
        billed, collected = totals['billed'] or 0, totals['collected'] or 0

        today = timezone.now().date()
        unpaid = invoices.exclude(status='paid').filter(due_date__lt=today)
        ageing = {}
        for label, lo, hi in (('0_30', 0, 30), ('31_60', 31, 60), ('61_90', 61, 90), ('90_plus', 91, None)):
            q = Q(due_date__lte=today - timedelta(days=lo))
            if hi is not None:
                q &= Q(due_date__gte=today - timedelta(days=hi))
            ageing[label] = unpaid.filter(q).aggregate(t=Sum(F('amount') - F('amount_paid')))['t'] or 0

        top_arrears = list(
            unpaid.values('lease__unit__property_id', 'lease__unit__property__name')
            .annotate(arrears=Sum(F('amount') - F('amount_paid'))).order_by('-arrears')[:5]
        )
        by_county = list(
            props.values('county').annotate(properties=Count('id', distinct=True),
                                            units=Count('units', distinct=True)).order_by('-properties')
        )
        review_counts = dict(props.values_list('review_state').annotate(c=Count('id')))
        oldest = (props.filter(review_state__in=['awaiting_landlord', 'awaiting_admin'])
                  .order_by('updated_at').values_list('updated_at', flat=True).first())

        return success({
            'filters': {k: qp.get(k) for k in ('county', 'property_type', 'landlord', 'agency', 'date_from', 'date_to')},
            'properties': {'total': props.count(), 'by_review_state': review_counts,
                           'oldest_pending_days': (timezone.now() - oldest).days if oldest else None},
            'units': {'total': total_units, 'occupied': occupied, 'vacant': units.filter(status='vacant').count(),
                      'occupancy_rate': round(occupied / total_units * 100, 1) if total_units else 0},
            'collections': {'billed': billed, 'collected': collected,
                            'collection_rate': round(float(collected) / float(billed) * 100, 1) if billed else 0,
                            'arrears_total': sum(ageing.values()), 'arrears_ageing': ageing},
            'top_arrears_properties': [
                {'property': str(r['lease__unit__property_id']), 'name': r['lease__unit__property__name'],
                 'arrears': r['arrears']} for r in top_arrears],
            'by_county': by_county,
            'failed_payments_30d': Payment.objects.filter(
                status='failed', created_at__gte=timezone.now() - timedelta(days=30)).count(),
        })
