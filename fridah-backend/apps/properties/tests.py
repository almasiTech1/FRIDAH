from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from apps.factories import UserFactory, LandlordFactory, PropertyFactory, UnitFactory
from apps.properties.models import Property


class PropertyListTests(APITestCase):
    def setUp(self):
        self.landlord = LandlordFactory(password="Pass123!")
        self.property = PropertyFactory(landlord=self.landlord, status=Property.Status.ACTIVE)
        UnitFactory(property=self.property)

    def test_public_can_list_active_properties(self):
        response = self.client.get(reverse('property_list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_landlord_can_create_property(self):
        self.client.force_authenticate(self.landlord)
        payload = {
            "name": "New Apartments", "property_type": "apartment",
            "county": "Nairobi", "town": "Lavington", "total_units": 4,
        }
        response = self.client.post(reverse('property_list'), payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Note: PropertyListCreateView is a plain generics.ListCreateAPIView, so unlike
        # most of the rest of the API it returns raw serializer data (no {success, data}
        # envelope), and PropertyCreateSerializer doesn't expose `status` at all. Both are
        # worth aligning with the rest of the API for consistency, but that's an API
        # contract change (could affect the web/mobile clients) rather than a test fix -
        # asserting the real DB state here instead of the unexposed field.
        created = Property.objects.get(id=response.data['id'])
        self.assertEqual(created.status, Property.Status.PENDING_APPROVAL)

    def test_tenant_cannot_create_property(self):
        tenant = UserFactory(password="Pass123!")
        self.client.force_authenticate(tenant)
        response = self.client.post(reverse('property_list'), {"name": "X"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
