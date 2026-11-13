from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.payments.models import Payment
from apps.rentals import amenities
from apps.rentals.models import AmenityCharge, Invoice

TODAY = date(2026, 3, 10)


@pytest.fixture
def live(property_):
    property_.review_state = property_.ReviewState.APPROVED
    property_.status = property_.Status.ACTIVE
    property_.save()
    return property_


@pytest.fixture
def charge(live, landlord):
    return AmenityCharge.objects.create(property=live, name='Security', amount=Decimal('500'), created_by=landlord)


@pytest.mark.django_db
class TestAmenityBilling:
    def test_bills_active_leases_once_per_month(self, charge, lease):
        assert amenities.generate_for_charge(charge, TODAY) == (1, 0)
        assert amenities.generate_for_charge(charge, TODAY) == (0, 1)        # idempotent
        inv = Invoice.objects.get(amenity_charge=charge)
        assert inv.invoice_type == 'amenity' and inv.amount == Decimal('500')
        assert inv.period_start == date(2026, 3, 1) and inv.period_end == date(2026, 3, 31)
        assert amenities.generate_for_charge(charge, date(2026, 4, 2)) == (1, 0)  # next month bills again

    def test_one_off_bills_once_ever(self, charge, lease):
        charge.frequency = 'one_off'
        charge.save()
        amenities.generate_for_charge(charge, TODAY)
        assert amenities.generate_for_charge(charge, date(2026, 4, 2)) == (0, 1)

    def test_exempt_lease_and_unit_scoping(self, api_client, charge, lease, landlord, unit):
        api_client.force_authenticate(user=landlord)
        r = api_client.post('/api/v1/amenity-exemptions/',
                            {'charge': str(charge.id), 'lease': str(lease.id), 'reason': 'Caretaker'}, format='json')
        assert r.status_code == 201
        assert amenities.generate_for_charge(charge, TODAY) == (0, 0)

    def test_inactive_charge_not_billed(self, charge, lease):
        charge.is_active = False
        charge.save()
        assert amenities.generate_all(TODAY)['created'] == 0

    def test_waiver_needs_reason_blocks_paid_and_is_audited(self, charge, lease, landlord):
        amenities.generate_for_charge(charge, TODAY)
        inv = Invoice.objects.get(amenity_charge=charge)
        with pytest.raises(ValidationError):
            amenities.waive_invoice(inv, landlord, '')
        amenities.waive_invoice(inv, landlord, 'Service outage')
        inv.refresh_from_db()
        assert inv.status == 'cancelled' and inv.waived_by_id == landlord.id
        from apps.audit.models import AuditLog
        assert AuditLog.objects.filter(action='amenity.invoice.waived').count() == 1
        paid = Invoice.objects.create(lease=lease, tenant=lease.tenant, invoice_type='amenity', amount=100,
                                      amount_paid=50, period_start=TODAY, period_end=TODAY, due_date=TODAY)
        with pytest.raises(ValidationError, match='refund'):
            amenities.waive_invoice(paid, landlord, 'x')

    def test_api_permissions(self, api_client, charge, tenant, stranger, landlord, live):
        payload = {'property': str(live.id), 'name': 'Gym', 'amount': '300'}
        for user in (tenant, stranger):
            api_client.force_authenticate(user=user)
            assert api_client.post('/api/v1/amenity-charges/', payload, format='json').status_code in (403, 400)
            assert api_client.get('/api/v1/amenity-charges/').data['results'] == []
        api_client.force_authenticate(user=landlord)
        assert api_client.post('/api/v1/amenity-charges/', payload, format='json').status_code == 201
        assert api_client.post('/api/v1/amenity-charges/', {**payload, 'amount': '0'}, format='json').status_code == 400


@pytest.mark.django_db
class TestReceiptVerification:
    def test_verifies_completed_payment_without_leaking_payer(self, api_client, tenant):
        p = Payment.objects.create(payer=tenant, amount=Decimal('1500'), method='mpesa_stk', status='completed',
                                   completed_at=timezone.now(), reference='PAY-ABC123XYZ')
        data = api_client.get('/api/v1/receipts/verify/?reference=pay-abc123xyz').data['data']
        assert data['valid'] is True and data['reference'] == p.reference
        assert not ({'payer', 'phone_number', 'phone'} & set(data))

    def test_unknown_pending_or_short_reference_is_not_valid(self, api_client, tenant):
        Payment.objects.create(payer=tenant, amount=10, status='pending', reference='PAY-PENDING01')
        assert api_client.get('/api/v1/receipts/verify/?reference=PAY-PENDING01').data['data']['valid'] is False
        assert api_client.get('/api/v1/receipts/verify/?reference=NOPE-NOPE-1').data['data']['valid'] is False
        assert api_client.get('/api/v1/receipts/verify/?reference=ab').status_code == 400


@pytest.mark.django_db
class TestAdminPortfolio:
    def test_admin_only_and_filters(self, api_client, admin_user, landlord, live, unit, lease, tenant):
        url = '/api/v1/analytics/dashboard/admin/portfolio/'
        api_client.force_authenticate(user=landlord)
        assert api_client.get(url).status_code == 403
        Invoice.objects.create(lease=lease, tenant=tenant, invoice_type='rent', amount=1000, amount_paid=400,
                               period_start=date(2026, 1, 1), period_end=date(2026, 1, 31), due_date=date(2026, 1, 5),
                               status='partially_paid')
        api_client.force_authenticate(user=admin_user)
        d = api_client.get(url).data['data']
        assert d['properties']['total'] == 1 and d['collections']['billed'] == 1000
        assert d['collections']['collection_rate'] == 40.0 and d['collections']['arrears_total'] == 600
        assert d['top_arrears_properties'][0]['arrears'] == 600
        assert api_client.get(url + '?county=Mombasa').data['data']['properties']['total'] == 0
