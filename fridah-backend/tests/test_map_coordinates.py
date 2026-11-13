"""Pinning a place with Google Maps: long coordinates are rounded and accepted, impossible ones are refused."""
from decimal import Decimal

import pytest

from apps.bookings.models import Listing
from apps.properties.models import Property

PROPERTY = {'name': 'Pinned', 'property_type': 'apartment', 'county': 'Nairobi', 'town': 'Westlands', 'total_units': 2}


@pytest.mark.django_db
class TestCoordinates:
    def test_google_style_long_coordinates_are_rounded_and_saved(self, api_client, landlord):
        api_client.force_authenticate(user=landlord)
        r = api_client.post('/api/v1/properties/', {**PROPERTY, 'latitude': -1.2920659123456, 'longitude': 36.8219462456789}, format='json')
        assert r.status_code == 201, r.data
        p = Property.objects.get(name='Pinned')
        assert p.latitude == Decimal('-1.292066') and p.longitude == Decimal('36.821946')

    def test_values_sent_as_text_work_too(self, api_client, landlord):
        api_client.force_authenticate(user=landlord)
        r = api_client.post('/api/v1/properties/', {**PROPERTY, 'latitude': '-1.29206591', 'longitude': '36.82194624'}, format='json')
        assert r.status_code == 201, r.data

    def test_coordinates_are_optional(self, api_client, landlord):
        api_client.force_authenticate(user=landlord)
        assert api_client.post('/api/v1/properties/', PROPERTY, format='json').status_code == 201
        assert api_client.post('/api/v1/properties/', {**PROPERTY, 'latitude': None, 'longitude': None}, format='json').status_code == 201

    @pytest.mark.parametrize('lat,lng', [(500, 36.8), (-91, 36.8), (-1.2, 181), (-1.2, -200)])
    def test_impossible_coordinates_are_refused(self, api_client, landlord, lat, lng):
        api_client.force_authenticate(user=landlord)
        r = api_client.post('/api/v1/properties/', {**PROPERTY, 'latitude': lat, 'longitude': lng}, format='json')
        assert r.status_code == 400
        assert not Property.objects.filter(name='Pinned').exists()

    def test_rubbish_is_refused_not_crashed(self, api_client, landlord):
        api_client.force_authenticate(user=landlord)
        assert api_client.post('/api/v1/properties/', {**PROPERTY, 'latitude': 'north', 'longitude': 36.8}, format='json').status_code == 400

    def test_hotel_listings_get_the_same_treatment(self, api_client, db):
        from apps.users.models import User
        host = User.objects.create_user(username='host1', email='host1@test.com', password='StrongPass123!', role='hotel_owner', phone_number='+254700000077')
        api_client.force_authenticate(user=host)
        body = {'name': 'Pinned Villa', 'listing_type': 'bnb', 'county': 'Kwale', 'town': 'Diani'}
        ok = api_client.post('/api/v1/listings/', {**body, 'latitude': -4.2799123456, 'longitude': 39.5917123456}, format='json')
        assert ok.status_code == 201, ok.data
        assert Listing.objects.get(name='Pinned Villa').latitude == Decimal('-4.279912')
        bad = api_client.post('/api/v1/listings/', {**body, 'name': 'Bad', 'latitude': 95, 'longitude': 39.5}, format='json')
        assert bad.status_code == 400
