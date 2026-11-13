from decimal import Decimal
from datetime import date

import pytest
from django.utils import timezone

from apps.rentals.models import Invoice, Lease
from apps.payments.models import Payment

FORECAST_URL = '/api/v1/analytics/analytics/revenue-forecast/'


@pytest.mark.django_db
class TestRevenueForecast:
    def test_perfect_collection_history_gives_100pct_rate(self, api_client, landlord, tenant, lease):
        invoice = Invoice.objects.create(
            lease=lease, tenant=tenant, invoice_type='rent', amount=Decimal('20000'), amount_paid=Decimal('20000'),
            period_start=date(2026, 6, 1), period_end=date(2026, 6, 30), due_date=date(2026, 6, 5),
            status=Invoice.Status.PAID,
        )
        api_client.force_authenticate(user=landlord)
        resp = api_client.get(FORECAST_URL)
        assert resp.status_code == 200
        assert resp.data['data']['historical_collection_rate_pct'] == 100.0

    def test_partial_collection_history_reduces_forecast(self, api_client, landlord, tenant, lease):
        Invoice.objects.create(
            lease=lease, tenant=tenant, invoice_type='rent', amount=Decimal('20000'), amount_paid=Decimal('10000'),
            period_start=date(2026, 6, 1), period_end=date(2026, 6, 30), due_date=date(2026, 6, 5),
            status=Invoice.Status.PARTIALLY_PAID,
        )
        api_client.force_authenticate(user=landlord)
        resp = api_client.get(FORECAST_URL)
        assert resp.data['data']['historical_collection_rate_pct'] == 50.0
        forecast = resp.data['data']['forecast']
        # active lease rent is 20000/month; at 50% historical collection, expected
        # collected should be materially less than billed
        assert forecast[0]['billed_revenue'] == 20000.0
        assert forecast[0]['expected_collected_revenue'] == 10000.0

    def test_no_billing_history_assumes_full_collection(self, api_client, landlord, lease):
        """With zero historical invoices, there's nothing to compute a real rate
        from - should default to 100% rather than divide by zero or return None."""
        api_client.force_authenticate(user=landlord)
        resp = api_client.get(FORECAST_URL)
        assert resp.status_code == 200
        assert resp.data['data']['historical_collection_rate_pct'] == 100.0

    def test_forecast_months_param_controls_length(self, api_client, landlord, lease):
        api_client.force_authenticate(user=landlord)
        resp = api_client.get(FORECAST_URL + '?forecast_months=3')
        assert len(resp.data['data']['forecast']) == 3

    def test_expired_lease_excluded_from_future_months(self, api_client, landlord, tenant, unit):
        Lease.objects.create(
            unit=unit, tenant=tenant, landlord=landlord, rent_amount=Decimal('15000'),
            deposit_amount=Decimal('15000'), start_date=date(2020, 1, 1), end_date=date(2020, 6, 30),
            rent_due_day=5, status=Lease.Status.TERMINATED,
        )
        api_client.force_authenticate(user=landlord)
        resp = api_client.get(FORECAST_URL)
        # terminated lease shouldn't count toward billed revenue at all (status filter)
        assert resp.data['data']['forecast'][0]['billed_revenue'] == 0.0
