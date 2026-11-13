from decimal import Decimal
from datetime import date

import pytest

from apps.properties.models import Property, Unit
from apps.rentals.models import Lease, RentalApplication
from apps.users.models import User

APPLY_URL = lambda unit_id: f'/api/v1/units/{unit_id}/apply/'
LIST_URL = '/api/v1/rental-applications/'
APPROVE_URL = lambda app_id: f'/api/v1/rental-applications/{app_id}/approve/'
REJECT_URL = lambda app_id: f'/api/v1/rental-applications/{app_id}/reject/'
WITHDRAW_URL = lambda app_id: f'/api/v1/rental-applications/{app_id}/withdraw/'


@pytest.fixture
def vacant_unit(property_):
    # Tenants can only apply to approved, listed properties.
    property_.review_state = Property.ReviewState.APPROVED
    property_.status = Property.Status.ACTIVE
    property_.save()
    return Unit.objects.create(
        property=property_, unit_number='B2', rent_amount=Decimal('18000'),
        deposit_amount=Decimal('18000'), bedrooms=2, bathrooms=1, status=Unit.Status.VACANT,
    )


@pytest.mark.django_db
class TestApplyToVacantUnit:
    def test_tenant_can_apply_to_vacant_unit(self, api_client, tenant, vacant_unit):
        api_client.force_authenticate(user=tenant)
        resp = api_client.post(APPLY_URL(vacant_unit.id), {
            'message': 'I would love to rent this unit', 'preferred_move_in_date': '2026-04-01',
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['data']['status'] == 'pending'
        assert RentalApplication.objects.filter(unit=vacant_unit, tenant=tenant).exists()

    def test_cannot_apply_to_occupied_unit(self, api_client, tenant, unit):
        """`unit` fixture already has an active lease from conftest, so it should
        not be VACANT-applyable even though it might still show status=vacant by
        default - explicitly set occupied here to test the real guard."""
        unit.status = Unit.Status.OCCUPIED
        unit.save()
        api_client.force_authenticate(user=tenant)
        resp = api_client.post(APPLY_URL(unit.id), {}, format='json')
        assert resp.status_code == 400

    def test_cannot_submit_duplicate_pending_application(self, api_client, tenant, vacant_unit):
        api_client.force_authenticate(user=tenant)
        api_client.post(APPLY_URL(vacant_unit.id), {}, format='json')
        resp = api_client.post(APPLY_URL(vacant_unit.id), {}, format='json')
        assert resp.status_code == 400

    def test_non_tenant_cannot_apply(self, api_client, landlord, vacant_unit):
        api_client.force_authenticate(user=landlord)
        resp = api_client.post(APPLY_URL(vacant_unit.id), {}, format='json')
        assert resp.status_code == 403


@pytest.mark.django_db
class TestReviewApplications:
    def test_landlord_sees_applications_for_own_property(self, api_client, landlord, tenant, vacant_unit):
        api_client.force_authenticate(user=tenant)
        api_client.post(APPLY_URL(vacant_unit.id), {}, format='json')

        api_client.force_authenticate(user=landlord)
        resp = api_client.get(LIST_URL)
        assert resp.status_code == 200
        results = resp.data.get('results', resp.data)
        assert len(results) == 1

    def test_stranger_landlord_does_not_see_others_applications(self, api_client, tenant, vacant_unit):
        api_client.force_authenticate(user=tenant)
        api_client.post(APPLY_URL(vacant_unit.id), {}, format='json')

        other_landlord = User.objects.create_user(
            username='other_ll_apply', email='other_ll_apply@test.com', password='x',
            role='landlord', phone_number='+254700666001',
        )
        api_client.force_authenticate(user=other_landlord)
        resp = api_client.get(LIST_URL)
        results = resp.data.get('results', resp.data)
        assert len(results) == 0

    def test_tenant_sees_only_own_applications(self, api_client, tenant, stranger, vacant_unit):
        api_client.force_authenticate(user=tenant)
        api_client.post(APPLY_URL(vacant_unit.id), {}, format='json')

        api_client.force_authenticate(user=stranger)
        resp = api_client.get(LIST_URL)
        results = resp.data.get('results', resp.data)
        assert len(results) == 0


@pytest.mark.django_db
class TestApproveApplication:
    def test_approving_creates_active_lease_and_marks_unit_occupied(self, api_client, landlord, tenant, vacant_unit):
        api_client.force_authenticate(user=tenant)
        create_resp = api_client.post(APPLY_URL(vacant_unit.id), {}, format='json')
        application_id = create_resp.data['data']['id']

        api_client.force_authenticate(user=landlord)
        resp = api_client.post(APPROVE_URL(application_id), {
            'rent_amount': '18000', 'deposit_amount': '18000', 'start_date': '2026-04-01',
        }, format='json')
        assert resp.status_code == 200
        assert resp.data['data']['lease']['status'] == 'active'

        vacant_unit.refresh_from_db()
        assert vacant_unit.status == Unit.Status.OCCUPIED
        application = RentalApplication.objects.get(id=application_id)
        assert application.status == RentalApplication.Status.APPROVED
        assert application.resulting_lease is not None

    def test_approving_one_application_auto_rejects_other_pending_ones(self, api_client, landlord, tenant, stranger, vacant_unit):
        api_client.force_authenticate(user=tenant)
        app1 = api_client.post(APPLY_URL(vacant_unit.id), {}, format='json').data['data']['id']

        api_client.force_authenticate(user=stranger)
        app2 = api_client.post(APPLY_URL(vacant_unit.id), {}, format='json').data['data']['id']

        api_client.force_authenticate(user=landlord)
        api_client.post(APPROVE_URL(app1), {}, format='json')

        app2_obj = RentalApplication.objects.get(id=app2)
        assert app2_obj.status == RentalApplication.Status.REJECTED

    def test_tenant_cannot_approve_their_own_application(self, api_client, tenant, vacant_unit):
        api_client.force_authenticate(user=tenant)
        app_id = api_client.post(APPLY_URL(vacant_unit.id), {}, format='json').data['data']['id']
        resp = api_client.post(APPROVE_URL(app_id), {}, format='json')
        assert resp.status_code == 403

    def test_stranger_landlord_cannot_approve(self, api_client, tenant, vacant_unit):
        api_client.force_authenticate(user=tenant)
        app_id = api_client.post(APPLY_URL(vacant_unit.id), {}, format='json').data['data']['id']

        other_landlord = User.objects.create_user(
            username='other_ll_approve', email='other_ll_approve@test.com', password='x',
            role='landlord', phone_number='+254700666002',
        )
        api_client.force_authenticate(user=other_landlord)
        resp = api_client.post(APPROVE_URL(app_id), {}, format='json')
        assert resp.status_code == 403


@pytest.mark.django_db
class TestRejectAndWithdraw:
    def test_landlord_can_reject_with_reason(self, api_client, landlord, tenant, vacant_unit):
        api_client.force_authenticate(user=tenant)
        app_id = api_client.post(APPLY_URL(vacant_unit.id), {}, format='json').data['data']['id']

        api_client.force_authenticate(user=landlord)
        resp = api_client.post(REJECT_URL(app_id), {'reason': 'Went with another applicant'}, format='json')
        assert resp.status_code == 200
        application = RentalApplication.objects.get(id=app_id)
        assert application.status == RentalApplication.Status.REJECTED
        assert application.rejection_reason == 'Went with another applicant'

        vacant_unit.refresh_from_db()
        assert vacant_unit.status == Unit.Status.VACANT  # rejection doesn't touch the unit

    def test_tenant_can_withdraw_own_pending_application(self, api_client, tenant, vacant_unit):
        api_client.force_authenticate(user=tenant)
        app_id = api_client.post(APPLY_URL(vacant_unit.id), {}, format='json').data['data']['id']
        resp = api_client.post(WITHDRAW_URL(app_id), {}, format='json')
        assert resp.status_code == 200
        assert RentalApplication.objects.get(id=app_id).status == RentalApplication.Status.WITHDRAWN

    def test_tenant_cannot_withdraw_someone_elses_application(self, api_client, tenant, stranger, vacant_unit):
        api_client.force_authenticate(user=tenant)
        app_id = api_client.post(APPLY_URL(vacant_unit.id), {}, format='json').data['data']['id']

        api_client.force_authenticate(user=stranger)
        resp = api_client.post(WITHDRAW_URL(app_id), {}, format='json')
        assert resp.status_code == 400
