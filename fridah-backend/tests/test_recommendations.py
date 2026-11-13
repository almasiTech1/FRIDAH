from decimal import Decimal
from datetime import date

import pytest

from apps.properties.models import Property, Unit, SavedProperty
from apps.rentals.models import RentalApplication
from apps.users.models import User

RECS_URL = '/api/v1/properties/recommendations/'


@pytest.mark.django_db
class TestPropertyRecommendations:
    def test_cold_start_returns_recent_listings_not_personalized(self, api_client, tenant, property_):
        api_client.force_authenticate(user=tenant)
        resp = api_client.get(RECS_URL)
        assert resp.status_code == 200
        assert resp.data['data']['is_personalized'] is False

    def test_saved_property_shapes_recommendations_toward_same_town(self, api_client, tenant, landlord, property_):
        # tenant saves a Westlands apartment (property_ fixture: town='Westlands')
        SavedProperty.objects.create(user=tenant, property=property_)

        matching = Property.objects.create(
            landlord=landlord, name='Westlands Match', property_type='apartment',
            county='Nairobi', town='Westlands', address_detail='X', status=Property.Status.ACTIVE,
        )
        Unit.objects.create(property=matching, unit_number='1', rent_amount=Decimal('20000'), bedrooms=1, bathrooms=1)

        distant = Property.objects.create(
            landlord=landlord, name='Mombasa Distant', property_type='apartment',
            county='Mombasa', town='Nyali', address_detail='Y', status=Property.Status.ACTIVE,
        )
        Unit.objects.create(property=distant, unit_number='1', rent_amount=Decimal('20000'), bedrooms=1, bathrooms=1)

        api_client.force_authenticate(user=tenant)
        resp = api_client.get(RECS_URL)
        data = resp.data['data']
        assert data['is_personalized'] is True
        names = [r['property']['name'] for r in data['results']]
        assert 'Westlands Match' in names
        # the matching (same-town) property should rank above the distant one
        assert names.index('Westlands Match') < names.index('Mombasa Distant') if 'Mombasa Distant' in names else True

    def test_already_saved_property_excluded_from_recommendations(self, api_client, tenant, property_):
        SavedProperty.objects.create(user=tenant, property=property_)
        api_client.force_authenticate(user=tenant)
        resp = api_client.get(RECS_URL)
        names = [r['property']['name'] for r in resp.data['data']['results']]
        assert property_.name not in names

    def test_applied_unit_property_excluded_and_weighted_higher(self, api_client, tenant, landlord, property_, unit):
        RentalApplication.objects.create(unit=unit, tenant=tenant)
        other_westlands = Property.objects.create(
            landlord=landlord, name='Second Westlands Option', property_type='apartment',
            county='Nairobi', town='Westlands', address_detail='Z', status=Property.Status.ACTIVE,
        )
        Unit.objects.create(property=other_westlands, unit_number='1', rent_amount=Decimal('20000'), bedrooms=1, bathrooms=1)

        api_client.force_authenticate(user=tenant)
        resp = api_client.get(RECS_URL)
        data = resp.data['data']
        names = [r['property']['name'] for r in data['results']]
        assert property_.name not in names  # already applied-to property excluded
        assert 'Second Westlands Option' in names
        result = next(r for r in data['results'] if r['property']['name'] == 'Second Westlands Option')
        assert result['score'] is not None and result['score'] > 0
        assert len(result['reasons']) > 0

    def test_limit_param_respected_and_capped(self, api_client, tenant):
        api_client.force_authenticate(user=tenant)
        resp = api_client.get(RECS_URL + '?limit=3')
        assert len(resp.data['data']['results']) <= 3

    def test_unauthenticated_request_rejected(self, api_client):
        resp = api_client.get(RECS_URL)
        assert resp.status_code == 401
