from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.users.models import User


@pytest.mark.django_db
class TestKYCFlow:
    def test_submitting_valid_document_sets_pending_status(self, api_client, tenant):
        api_client.force_authenticate(user=tenant)
        doc = SimpleUploadedFile('id_front.jpg', b'fake jpg bytes', content_type='image/jpeg')
        resp = api_client.post('/api/v1/kyc/submit/', {
            'national_id': '87654321', 'kyc_document': doc,
        }, format='multipart')
        assert resp.status_code == 200
        tenant.refresh_from_db()
        assert tenant.kyc_status == User.KYCStatus.PENDING
        assert tenant.kyc_document.name.endswith('.jpg')

    def test_submitting_disallowed_file_type_rejected(self, api_client, tenant):
        """Confirms the new common/validators.py extension allow-list is actually
        wired into the real KYC submission endpoint, not just the model definition."""
        api_client.force_authenticate(user=tenant)
        doc = SimpleUploadedFile('id_front.exe', b'MZ\x90\x00', content_type='application/octet-stream')
        resp = api_client.post('/api/v1/kyc/submit/', {
            'national_id': '87654321', 'kyc_document': doc,
        }, format='multipart')
        assert resp.status_code == 400

    def test_admin_can_approve_pending_kyc(self, api_client, tenant, admin_user):
        tenant.kyc_status = User.KYCStatus.PENDING
        tenant.national_id = '87654321'
        tenant.save()
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post(f'/api/v1/kyc/{tenant.id}/review/', {'action': 'approve'}, format='json')
        assert resp.status_code == 200
        tenant.refresh_from_db()
        assert tenant.kyc_status == User.KYCStatus.VERIFIED
        assert tenant.kyc_reviewed_by == admin_user

    def test_admin_can_reject_pending_kyc_with_reason(self, api_client, tenant, admin_user):
        tenant.kyc_status = User.KYCStatus.PENDING
        tenant.save()
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post(f'/api/v1/kyc/{tenant.id}/review/', {
            'action': 'reject', 'rejection_reason': 'Document is blurry, please resubmit.',
        }, format='json')
        assert resp.status_code == 200
        tenant.refresh_from_db()
        assert tenant.kyc_status == User.KYCStatus.REJECTED
        assert tenant.kyc_rejection_reason == 'Document is blurry, please resubmit.'

    def test_non_admin_cannot_review_kyc(self, api_client, tenant, landlord):
        tenant.kyc_status = User.KYCStatus.PENDING
        tenant.save()
        api_client.force_authenticate(user=landlord)
        resp = api_client.post(f'/api/v1/kyc/{tenant.id}/review/', {'action': 'approve'}, format='json')
        assert resp.status_code == 403

    def test_pending_kyc_list_only_shows_admin(self, api_client, tenant, landlord, admin_user):
        tenant.kyc_status = User.KYCStatus.PENDING
        tenant.save()
        api_client.force_authenticate(user=landlord)
        assert api_client.get('/api/v1/kyc/pending/').status_code == 403
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get('/api/v1/kyc/pending/')
        assert resp.status_code == 200
        items = resp.data.get('results', resp.data.get('data', resp.data))
        ids = [str(u['id']) for u in items]
        assert str(tenant.id) in ids


@pytest.mark.django_db
class TestPropertyApprovalFlow:
    def test_new_property_defaults_to_pending_approval(self, api_client, landlord):
        api_client.force_authenticate(user=landlord)
        resp = api_client.post('/api/v1/properties/', {
            'name': 'Riverside Court', 'property_type': 'apartment',
            'county': 'Nairobi', 'town': 'Kilimani', 'total_units': 6,
        }, format='json')
        assert resp.status_code == 201
        from apps.properties.models import Property
        prop = Property.objects.get(id=resp.data['id'])
        assert prop.status == Property.Status.PENDING_APPROVAL

    def test_admin_can_approve_property(self, api_client, landlord, property_, admin_user):
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post(f'/api/v1/properties/{property_.id}/approval/', {'action': 'approve'}, format='json')
        assert resp.status_code == 200
        property_.refresh_from_db()
        from apps.properties.models import Property
        assert property_.status == Property.Status.ACTIVE

    def test_landlord_cannot_self_approve_property(self, api_client, landlord, property_):
        api_client.force_authenticate(user=landlord)
        resp = api_client.post(f'/api/v1/properties/{property_.id}/approval/', {'action': 'approve'}, format='json')
        assert resp.status_code == 403

    def test_admin_can_suspend_active_property(self, api_client, property_, admin_user):
        from apps.properties.models import Property
        # A property can only be live once its approvals are complete (enforced in Property.save()).
        property_.review_state = Property.ReviewState.APPROVED
        property_.status = Property.Status.ACTIVE
        property_.save()
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post(f'/api/v1/properties/{property_.id}/approval/', {'action': 'suspend'}, format='json')
        assert resp.status_code == 200
        property_.refresh_from_db()
        assert property_.status == Property.Status.SUSPENDED

    def test_agency_managed_property_still_goes_through_same_admin_approval(self, api_client, landlord, property_, admin_user):
        """Agencies never own properties directly (landlord always does), so the
        same admin approval endpoint covers agency-managed listings too - confirming
        there's no separate/missing approval path for the agency workflow."""
        from apps.agencies import services as agency_services
        from datetime import date
        agency = agency_services.create_agency(name='Prime Property Managers', created_by=landlord, email='ops@prime.co.ke')
        agency_services.assign_property_to_agency(
            property=property_, agency=agency, start_date=date(2026, 1, 1),
            management_fee_percent=Decimal('10'), approved_by=landlord,
        )
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post(f'/api/v1/properties/{property_.id}/approval/', {'action': 'approve'}, format='json')
        assert resp.status_code == 200
        property_.refresh_from_db()
        from apps.properties.models import Property
        assert property_.status == Property.Status.ACTIVE
