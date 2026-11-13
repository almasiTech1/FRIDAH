from decimal import Decimal
from datetime import date

import pytest
from django.utils import timezone

from apps.properties.models import SavedProperty
from apps.rentals.models import Lease
from apps.users.models import User

FUNNEL_URL = '/api/v1/analytics/analytics/leasing-funnel/'


@pytest.mark.django_db
class TestLeasingFunnelAnalytics:
    def test_landlord_sees_saves_and_lease_conversion_for_own_property(self, api_client, landlord, tenant, property_, unit):
        SavedProperty.objects.create(user=tenant, property=property_)
        other_saver = User.objects.create_user(
            username='saver2', email='saver2@test.com', password='x',
            role='tenant', phone_number='+254700444001',
        )
        SavedProperty.objects.create(user=other_saver, property=property_)

        Lease.objects.create(
            unit=unit, tenant=tenant, landlord=landlord, rent_amount=Decimal('20000'),
            deposit_amount=Decimal('20000'), start_date=date(2026, 1, 1),
            rent_due_day=5, status=Lease.Status.ACTIVE,
        )

        api_client.force_authenticate(user=landlord)
        resp = api_client.get(FUNNEL_URL)
        assert resp.status_code == 200
        funnel = resp.data['data']['funnel']
        assert funnel['total_saves'] == 2
        assert funnel['properties_saved'] == 1
        assert funnel['leases_created'] == 1
        assert funnel['leases_activated'] == 1

        rates = resp.data['data']['conversion_rates']
        assert rates['save_to_lease_created_pct'] == 50.0  # 1 lease / 2 saves
        assert rates['lease_created_to_active_pct'] == 100.0

    def test_top_properties_breakdown_scoped_per_property(self, api_client, landlord, tenant, property_):
        SavedProperty.objects.create(user=tenant, property=property_)
        api_client.force_authenticate(user=landlord)
        resp = api_client.get(FUNNEL_URL)
        top = resp.data['data']['top_properties_by_saves']
        assert len(top) == 1
        assert top[0]['property_id'] == str(property_.id)
        assert top[0]['saves'] == 1

    def test_stranger_landlord_sees_no_data_for_others_properties(self, api_client, tenant, property_):
        SavedProperty.objects.create(user=tenant, property=property_)
        other_landlord = User.objects.create_user(
            username='other_ll_funnel', email='other_ll_funnel@test.com', password='x',
            role='landlord', phone_number='+254700444002',
        )
        api_client.force_authenticate(user=other_landlord)
        resp = api_client.get(FUNNEL_URL)
        assert resp.data['data']['funnel']['total_saves'] == 0

    def test_days_param_excludes_old_saves(self, api_client, landlord, tenant, property_):
        old_save = SavedProperty.objects.create(user=tenant, property=property_)
        SavedProperty.objects.filter(id=old_save.id).update(
            created_at=timezone.now() - timezone.timedelta(days=90)
        )
        api_client.force_authenticate(user=landlord)
        resp = api_client.get(FUNNEL_URL + '?days=7')
        assert resp.data['data']['funnel']['total_saves'] == 0

        resp2 = api_client.get(FUNNEL_URL + '?days=120')
        assert resp2.data['data']['funnel']['total_saves'] == 1

    def test_agency_leasing_agent_only_sees_assigned_properties(self, api_client, landlord, tenant, property_):
        from apps.agencies import services as agency_services
        from apps.agencies.models import AgencyMembership, AgencyRole, PropertyStaffAssignment
        from apps.properties.models import Property

        agency = agency_services.create_agency(name='Funnel Agency', created_by=landlord, email='ops@funnel.co.ke')
        agency_services.assign_property_to_agency(
            property=property_, agency=agency, start_date=date(2026, 1, 1),
            management_fee_percent=Decimal('10'), approved_by=landlord,
        )
        other_property = Property.objects.create(
            landlord=landlord, name='Other Funnel Building', property_type='apartment',
            county='Nairobi', town='Karen', address_detail='999 Rd',
        )
        agency_services.assign_property_to_agency(
            property=other_property, agency=agency, start_date=date(2026, 1, 1),
            management_fee_percent=Decimal('10'), approved_by=landlord,
        )
        SavedProperty.objects.create(user=tenant, property=property_)
        SavedProperty.objects.create(user=tenant, property=other_property)

        agent_role = AgencyRole.objects.get(agency=agency, role_type=AgencyRole.RoleType.LEASING_AGENT)
        agent_user = User.objects.create_user(
            username='leasing_agent1', email='leasing_agent1@test.com', password='x',
            role='tenant', phone_number='+254700444003',
        )
        agent_membership = AgencyMembership.objects.create(
            agency=agency, user=agent_user, role=agent_role, status=AgencyMembership.Status.ACTIVE,
        )
        PropertyStaffAssignment.objects.create(membership=agent_membership, property=property_, is_active=True)

        api_client.force_authenticate(user=agent_user)
        resp = api_client.get(FUNNEL_URL)
        assert resp.data['data']['funnel']['total_saves'] == 1  # only property_, not other_property
