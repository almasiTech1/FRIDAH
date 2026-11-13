from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.analytics.views import monthly_totals
from apps.payments.models import Payment, Payout
from apps.rentals.models import Invoice

LANDLORD_URL = '/api/v1/analytics/dashboard/landlord/'
ADMIN_URL = '/api/v1/analytics/dashboard/admin/'


def months_ago(n):
    now = timezone.now().replace(day=15, hour=10, minute=0, second=0, microsecond=0)
    y, m = now.year, now.month - n
    while m <= 0:
        y, m = y - 1, m + 12
    return now.replace(year=y, month=m)


def pay(payer, amount, when, invoice=None, status=Payment.Status.COMPLETED):
    return Payment.objects.create(payer=payer, invoice=invoice, amount=Decimal(amount), status=status, completed_at=when)


@pytest.mark.django_db
class TestMonthlyHistory:
    def test_landlord_gets_twelve_ordered_months_with_zero_fill(self, api_client, landlord, tenant, lease):
        inv = Invoice.objects.create(lease=lease, tenant=tenant, invoice_type='rent', amount=Decimal('20000'), amount_paid=Decimal('20000'),
                                     period_start=date(2026, 1, 1), period_end=date(2026, 1, 31), due_date=date(2026, 1, 5), status=Invoice.Status.PAID)
        pay(tenant, '20000', months_ago(0), inv)
        pay(tenant, '15000', months_ago(2), inv)
        pay(tenant, '5000', months_ago(2), inv)
        pay(tenant, '99999', months_ago(1), inv, status=Payment.Status.FAILED)  # failed payments never count
        api_client.force_authenticate(user=landlord)
        series = api_client.get(LANDLORD_URL).data['data']['collected_by_month']
        assert len(series) == 12
        assert [r['month'] for r in series] == sorted(r['month'] for r in series)
        assert series[-1]['amount'] == 20000.0           # this month
        assert series[-2]['amount'] == 0.0               # failed payment ignored, gap filled with 0
        assert series[-3]['amount'] == 20000.0           # two payments summed
        assert series[0]['amount'] == 0.0

    def test_landlord_only_sees_their_own_money(self, api_client, landlord, tenant, stranger, lease):
        inv = Invoice.objects.create(lease=lease, tenant=tenant, invoice_type='rent', amount=Decimal('1000'),
                                     period_start=date(2026, 1, 1), period_end=date(2026, 1, 31), due_date=date(2026, 1, 5))
        pay(tenant, '1000', months_ago(0), inv)
        pay(stranger, '777', months_ago(0))  # unrelated payment, no invoice on this landlord's lease
        api_client.force_authenticate(user=landlord)
        assert api_client.get(LANDLORD_URL).data['data']['collected_by_month'][-1]['amount'] == 1000.0

    def test_admin_gets_revenue_and_payout_history(self, api_client, admin_user, tenant, landlord):
        pay(tenant, '30000', months_ago(0)); pay(tenant, '12000', months_ago(3))
        Payout.objects.create(recipient=landlord, amount=Decimal('25000'), phone_number='+254700000001', status='completed', completed_at=months_ago(0))
        api_client.force_authenticate(user=admin_user)
        data = api_client.get(ADMIN_URL).data['data']
        assert data['revenue_by_month'][-1]['amount'] == 30000.0 and data['revenue_by_month'][-4]['amount'] == 12000.0
        assert data['payouts_by_month'][-1]['amount'] == 25000.0

    def test_helper_handles_a_year_boundary_and_custom_length(self, db, tenant):
        pay(tenant, '100', months_ago(5))
        out = monthly_totals(Payment.objects.filter(status='completed'), 'completed_at', months=6)
        assert len(out) == 6 and out[0]['amount'] == 100.0


@pytest.mark.django_db
class TestAgencyAndTileConsistency:
    def test_landlord_tile_matches_the_chart_and_counts_partial_payments(self, api_client, landlord, tenant, lease):
        inv = Invoice.objects.create(lease=lease, tenant=tenant, invoice_type='rent', amount=Decimal('20000'), amount_paid=Decimal('8000'),
                                     period_start=date(2026, 1, 1), period_end=date(2026, 1, 31), due_date=date(2026, 1, 5), status=Invoice.Status.PARTIALLY_PAID)
        pay(tenant, '8000', months_ago(0), inv)   # a part-payment on an invoice that is not fully paid yet
        api_client.force_authenticate(user=landlord)
        data = api_client.get(LANDLORD_URL).data['data']
        assert data['collected_this_month'] == 8000.0
        assert data['collected_this_month'] == data['collected_by_month'][-1]['amount']

    def test_agency_rollup_returns_history_for_its_own_properties_only(self, api_client, landlord, tenant, lease, property_):
        from apps.agencies import services as agency_services
        agency = agency_services.create_agency(name='Prime Property Managers', created_by=landlord, email='ops@prime.co.ke')
        agency_services.assign_property_to_agency(property=property_, agency=agency, start_date=date(2026, 1, 1),
                                                  management_fee_percent=Decimal('10'), approved_by=landlord)
        inv = Invoice.objects.create(lease=lease, tenant=tenant, invoice_type='rent', amount=Decimal('20000'),
                                     period_start=date(2026, 1, 1), period_end=date(2026, 1, 31), due_date=date(2026, 1, 5))
        pay(tenant, '20000', months_ago(1), inv)
        pay(tenant, '500', months_ago(1))  # unrelated payment (no invoice) must not be counted
        api_client.force_authenticate(user=landlord)
        series = api_client.get(f'/api/v1/agencies/{agency.id}/dashboard/').data['data']['collected_by_month']
        assert len(series) == 12 and series[-2]['amount'] == 20000.0 and series[-1]['amount'] == 0.0


@pytest.mark.django_db
class TestProviderEarningsHistory:
    def test_provider_sees_only_their_own_credits_per_month(self, api_client, db, tenant):
        from apps.payments.models import WalletTransaction
        from apps.users.models import User
        provider = User.objects.create_user(username='prov1', email='prov1@test.com', password='StrongPass123!', role='service_provider', phone_number='+254700000055')
        def credit(user, amount, when, kind='credit'):
            row = WalletTransaction.objects.create(user=user, entry_type=kind, amount=Decimal(amount), balance_after=Decimal(amount))
            WalletTransaction.objects.filter(pk=row.pk).update(created_at=when)   # created_at is auto-set, so backdate it
        credit(provider, '9000', months_ago(0)); credit(provider, '4000', months_ago(0)); credit(provider, '2500', months_ago(2))
        credit(provider, '3000', months_ago(0), kind='debit')   # a withdrawal is not an earning
        credit(tenant, '777', months_ago(0))                    # someone else's wallet
        api_client.force_authenticate(user=provider)
        series = api_client.get('/api/v1/analytics/dashboard/service-provider/').data['data']['earnings_by_month']
        assert len(series) == 12 and series[-1]['amount'] == 13000.0 and series[-3]['amount'] == 2500.0 and series[-2]['amount'] == 0.0
