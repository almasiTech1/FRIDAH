"""End to end: once a house is approved and listed, a tenant can open it and apply for a vacant unit."""
import pytest

from apps.properties.models import Property
from apps.rentals.models import RentalApplication


@pytest.mark.django_db
class TestTenantApplyAfterApproval:
    def approve(self, api_client, admin_user, property_):
        api_client.force_authenticate(user=admin_user)
        assert api_client.post(f'/api/v1/properties/{property_.id}/approval/', {'action': 'approve'}, format='json').status_code == 200
        property_.refresh_from_db()
        assert property_.status == Property.Status.ACTIVE

    def test_tenant_can_see_and_apply_for_an_approved_unit(self, api_client, admin_user, tenant, property_, unit):
        self.approve(api_client, admin_user, property_)
        api_client.force_authenticate(user=tenant)

        listed = api_client.get('/api/v1/properties/')
        ids = [p['id'] for p in (listed.data.get('data', listed.data).get('results') or listed.data.get('results') or [])]
        assert str(property_.id) in ids

        detail = api_client.get(f'/api/v1/properties/{property_.id}/')
        assert detail.status_code == 200
        body = detail.data.get('data', detail.data)
        assert [u['status'] for u in body['units']] == ['vacant']

        resp = api_client.post(f'/api/v1/units/{unit.id}/apply/', {'message': 'I would like to rent this.'}, format='json')
        assert resp.status_code == 201, resp.data
        assert RentalApplication.objects.filter(unit=unit, tenant=tenant, status='pending').count() == 1

    def test_applying_twice_is_refused_with_a_clear_message(self, api_client, admin_user, tenant, property_, unit):
        self.approve(api_client, admin_user, property_)
        api_client.force_authenticate(user=tenant)
        api_client.post(f'/api/v1/units/{unit.id}/apply/', {}, format='json')
        again = api_client.post(f'/api/v1/units/{unit.id}/apply/', {}, format='json')
        assert again.status_code == 400 and 'pending application' in again.data['error']['message']

    def test_cannot_apply_to_a_property_that_is_not_approved_and_listed(self, api_client, tenant, property_, unit):
        api_client.force_authenticate(user=tenant)       # property_ is still pending approval here
        resp = api_client.post(f'/api/v1/units/{unit.id}/apply/', {}, format='json')
        assert resp.status_code == 400 and 'not currently listed' in resp.data['error']['message']
        assert not RentalApplication.objects.filter(unit=unit).exists()
