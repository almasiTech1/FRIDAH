import pytest
from decimal import Decimal
from datetime import date

from apps.users.models import User


@pytest.mark.django_db
class TestGlobalSearch:
    def test_short_query_returns_empty_results(self, api_client, landlord):
        api_client.force_authenticate(user=landlord)
        resp = api_client.get('/api/v1/search/?q=a')
        assert resp.status_code == 200
        assert resp.data['data']['total_results'] == 0

    def test_landlord_finds_own_property_by_name(self, api_client, landlord, property_):
        api_client.force_authenticate(user=landlord)
        resp = api_client.get('/api/v1/search/?q=Sunset')
        assert resp.status_code == 200
        names = [p['name'] for p in resp.data['data']['results']['properties']]
        assert 'Sunset Apartments' in names

    def test_landlord_does_not_find_other_landlords_property(self, api_client, landlord, property_):
        other_landlord = User.objects.create_user(
            username='other_ll_search', email='other_ll_search@test.com', password='x',
            role='landlord', phone_number='+254700333001',
        )
        api_client.force_authenticate(user=other_landlord)
        resp = api_client.get('/api/v1/search/?q=Sunset')
        assert resp.data['data']['results'].get('properties', []) == []

    def test_tenant_can_search_for_own_lease_but_not_others(self, api_client, tenant, lease):
        api_client.force_authenticate(user=tenant)
        resp = api_client.get(f'/api/v1/search/?q={lease.unit.unit_number}&types=leases')
        assert resp.status_code == 200
        assert len(resp.data['data']['results']['leases']) == 1

    def test_stranger_tenant_cannot_search_leases_they_dont_own(self, api_client, stranger, lease):
        api_client.force_authenticate(user=stranger)
        resp = api_client.get(f'/api/v1/search/?q={lease.unit.unit_number}&types=leases')
        assert resp.data['data']['results'].get('leases', []) == []

    def test_users_search_hidden_from_non_admin(self, api_client, landlord, tenant):
        api_client.force_authenticate(user=landlord)
        resp = api_client.get(f'/api/v1/search/?q={tenant.username}&types=users')
        # 'users' key should not even appear - it's a permission-gated category, not an empty list
        assert 'users' not in resp.data['data']['results']

    def test_admin_can_search_users(self, api_client, admin_user, tenant):
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get(f'/api/v1/search/?q={tenant.username}&types=users')
        assert resp.status_code == 200
        found = [u['id'] for u in resp.data['data']['results']['users']]
        assert str(tenant.id) in found

    def test_types_filter_limits_categories_returned(self, api_client, landlord, property_):
        api_client.force_authenticate(user=landlord)
        resp = api_client.get('/api/v1/search/?q=Sunset&types=properties')
        assert set(resp.data['data']['results'].keys()) <= {'properties'}

    def test_agency_search_visible_to_any_authenticated_user(self, api_client, landlord, stranger):
        from apps.agencies import services as agency_services
        agency_services.create_agency(name='Zenith Realty', created_by=landlord, email='ops@zenith.co.ke')
        api_client.force_authenticate(user=stranger)
        resp = api_client.get('/api/v1/search/?q=Zenith&types=agencies')
        names = [a['name'] for a in resp.data['data']['results']['agencies']]
        assert 'Zenith Realty' in names

    def test_agency_staffed_property_manager_finds_assigned_property_only(self, api_client, landlord, tenant, property_):
        from apps.agencies import services as agency_services
        from apps.agencies.models import AgencyMembership, AgencyRole, PropertyStaffAssignment
        from apps.properties.models import Property

        agency = agency_services.create_agency(name='Prime Managers Search', created_by=landlord, email='ops@prime.co.ke')
        agency_services.assign_property_to_agency(
            property=property_, agency=agency, start_date=date(2026, 1, 1),
            management_fee_percent=Decimal('10'), approved_by=landlord,
        )
        other_property = Property.objects.create(
            landlord=landlord, name='Unassigned Towers', property_type='apartment',
            county='Nairobi', town='Karen', address_detail='789 Rd',
        )
        agency_services.assign_property_to_agency(
            property=other_property, agency=agency, start_date=date(2026, 1, 1),
            management_fee_percent=Decimal('10'), approved_by=landlord,
        )

        pm_role = AgencyRole.objects.get(agency=agency, role_type=AgencyRole.RoleType.PROPERTY_MANAGER)
        pm_membership = AgencyMembership.objects.create(
            agency=agency, user=tenant, role=pm_role, status=AgencyMembership.Status.ACTIVE,
        )
        PropertyStaffAssignment.objects.create(membership=pm_membership, property=property_, is_active=True)

        api_client.force_authenticate(user=tenant)
        resp = api_client.get('/api/v1/search/?q=Towers&types=properties')
        assert resp.data['data']['results']['properties'] == []  # not assigned to Unassigned Towers

        resp2 = api_client.get('/api/v1/search/?q=Sunset&types=properties')
        names = [p['name'] for p in resp2.data['data']['results']['properties']]
        assert 'Sunset Apartments' in names
