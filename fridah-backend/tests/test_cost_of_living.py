from decimal import Decimal
from datetime import date

import pytest

from apps.properties.models import Unit
from apps.rentals.models import UtilityAccount, Invoice


@pytest.fixture
def cost_unit(property_):
    # This endpoint is public, so the property must be a published (approved) listing.
    property_.review_state = property_.ReviewState.APPROVED
    property_.status = property_.Status.ACTIVE
    property_.save()
    return Unit.objects.create(
        property=property_, unit_number='C3', rent_amount=Decimal('25000'),
        deposit_amount=Decimal('25000'), bedrooms=1, bathrooms=1, status=Unit.Status.VACANT,
    )


@pytest.mark.django_db
class TestCostOfLiving:
    def test_rent_only_with_no_utility_accounts(self, api_client, cost_unit):
        resp = api_client.get(f'/api/v1/units/{cost_unit.id}/cost-of-living/')
        assert resp.status_code == 200
        data = resp.data['data']
        assert data['rent'] == '25000.00' or data['rent'] == '25000'
        assert data['utilities'] == []
        assert Decimal(data['platform_total']) == Decimal('25000.00')

    def test_flat_fee_utility_included_directly(self, api_client, cost_unit):
        UtilityAccount.objects.create(
            unit=cost_unit, utility_type=UtilityAccount.UtilityType.GARBAGE,
            is_metered=False, flat_monthly_fee=Decimal('500'), is_active=True,
        )
        resp = api_client.get(f'/api/v1/units/{cost_unit.id}/cost-of-living/')
        data = resp.data['data']
        garbage_line = next(u for u in data['utilities'] if u['utility_type'] == 'garbage')
        assert garbage_line['basis'] == 'flat_fee'
        assert Decimal(garbage_line['monthly_estimate']) == Decimal('500')
        assert Decimal(data['platform_total']) == Decimal('25500.00')

    def test_metered_utility_with_no_history_reports_no_data(self, api_client, cost_unit):
        UtilityAccount.objects.create(
            unit=cost_unit, utility_type=UtilityAccount.UtilityType.ELECTRICITY,
            is_metered=True, rate_per_unit=Decimal('25'), is_active=True,
        )
        resp = api_client.get(f'/api/v1/units/{cost_unit.id}/cost-of-living/')
        data = resp.data['data']
        elec_line = next(u for u in data['utilities'] if u['utility_type'] == 'electricity')
        assert elec_line['basis'] == 'no_data'
        assert elec_line['monthly_estimate'] is None
        assert Decimal(data['platform_total']) == Decimal('25000.00')

    def test_metered_utility_with_history_uses_real_average(self, api_client, cost_unit, tenant, landlord):
        UtilityAccount.objects.create(
            unit=cost_unit, utility_type=UtilityAccount.UtilityType.WATER,
            is_metered=True, rate_per_unit=Decimal('10'), is_active=True,
        )
        from apps.rentals.models import Lease
        lease = Lease.objects.create(
            unit=cost_unit, tenant=tenant, landlord=landlord, rent_amount=Decimal('25000'),
            deposit_amount=Decimal('25000'), start_date=date(2026, 1, 1), rent_due_day=5,
            status=Lease.Status.ACTIVE,
        )
        for amount in [Decimal('800'), Decimal('1000'), Decimal('1200')]:
            Invoice.objects.create(
                lease=lease, tenant=tenant, invoice_type=Invoice.InvoiceType.UTILITY,
                amount=amount, period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
                due_date=date(2026, 1, 5),
            )
        resp = api_client.get(f'/api/v1/units/{cost_unit.id}/cost-of-living/')
        data = resp.data['data']
        water_line = next(u for u in data['utilities'] if u['utility_type'] == 'water')
        assert water_line['basis'] == 'historical_average'
        assert Decimal(water_line['monthly_estimate']) == Decimal('1000.00')

    def test_inactive_utility_account_excluded(self, api_client, cost_unit):
        UtilityAccount.objects.create(
            unit=cost_unit, utility_type=UtilityAccount.UtilityType.INTERNET,
            is_metered=False, flat_monthly_fee=Decimal('3000'), is_active=False,
        )
        resp = api_client.get(f'/api/v1/units/{cost_unit.id}/cost-of-living/')
        data = resp.data['data']
        assert data['utilities'] == []

    def test_endpoint_is_public_no_auth_required(self, api_client, cost_unit):
        resp = api_client.get(f'/api/v1/units/{cost_unit.id}/cost-of-living/')
        assert resp.status_code == 200
