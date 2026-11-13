import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.rentals.models import MaintenanceRequest, MaintenanceImage
from apps.users.models import User


@pytest.fixture
def maintenance_request(tenant, unit):
    return MaintenanceRequest.objects.create(
        tenant=tenant, unit=unit, category='plumbing', title='Leaking tap',
        description='Kitchen tap is leaking', priority='medium', status='open',
    )


@pytest.mark.django_db
class TestMaintenanceImageUpload:
    def test_tenant_can_attach_photo_to_own_request(self, api_client, tenant, maintenance_request):
        api_client.force_authenticate(user=tenant)
        photo = _fake_jpeg()
        resp = api_client.post(
            f'/api/v1/maintenance/{maintenance_request.id}/images/', {'image': photo}, format='multipart',
        )
        assert resp.status_code == 201
        assert MaintenanceImage.objects.filter(request=maintenance_request).count() == 1

    def test_landlord_can_attach_photo_of_completed_repair(self, api_client, landlord, maintenance_request):
        api_client.force_authenticate(user=landlord)
        resp = api_client.post(
            f'/api/v1/maintenance/{maintenance_request.id}/images/', {'image': _fake_jpeg()}, format='multipart',
        )
        assert resp.status_code == 201

    def test_stranger_cannot_attach_photo(self, api_client, stranger, maintenance_request):
        api_client.force_authenticate(user=stranger)
        resp = api_client.post(
            f'/api/v1/maintenance/{maintenance_request.id}/images/', {'image': _fake_jpeg()}, format='multipart',
        )
        assert resp.status_code == 403

    def test_missing_image_returns_400(self, api_client, tenant, maintenance_request):
        api_client.force_authenticate(user=tenant)
        resp = api_client.post(f'/api/v1/maintenance/{maintenance_request.id}/images/', {}, format='multipart')
        assert resp.status_code == 400

    def test_uploaded_image_appears_on_request_detail(self, api_client, tenant, maintenance_request):
        api_client.force_authenticate(user=tenant)
        api_client.post(f'/api/v1/maintenance/{maintenance_request.id}/images/', {'image': _fake_jpeg()}, format='multipart')
        resp = api_client.get(f'/api/v1/maintenance/{maintenance_request.id}/')
        assert len(resp.data['images']) == 1


def _fake_jpeg():
    # Minimal valid JPEG bytes so Django's ImageField (Pillow-backed) validation passes.
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new('RGB', (10, 10), color='red').save(buf, format='JPEG')
    buf.seek(0)
    return SimpleUploadedFile('issue.jpg', buf.read(), content_type='image/jpeg')
