import pytest
from decimal import Decimal
from datetime import date
from rest_framework.test import APIClient

from apps.users.models import User
from apps.properties.models import Property, Unit
from apps.rentals.models import Lease


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def landlord(db):
    return User.objects.create_user(
        username='landlord1', email='landlord1@test.com', password='StrongPass123!',
        role='landlord', phone_number='+254700000001',
    )


@pytest.fixture
def tenant(db):
    return User.objects.create_user(
        username='tenant1', email='tenant1@test.com', password='StrongPass123!',
        role='tenant', phone_number='+254700000003',
    )


@pytest.fixture
def stranger(db):
    return User.objects.create_user(
        username='stranger1', email='stranger1@test.com', password='StrongPass123!',
        role='tenant', phone_number='+254700000004',
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username='admin1', email='admin1@test.com', password='StrongPass123!',
        phone_number='+254700000099',
    )


@pytest.fixture
def property_(db, landlord):
    return Property.objects.create(
        landlord=landlord, name='Sunset Apartments', property_type='apartment',
        county='Nairobi', town='Westlands', address_detail='123 St',
    )


@pytest.fixture
def unit(db, property_):
    return Unit.objects.create(
        property=property_, unit_number='A1', rent_amount=Decimal('20000'),
        bedrooms=1, bathrooms=1,
    )


@pytest.fixture
def lease(db, unit, tenant, landlord):
    return Lease.objects.create(
        unit=unit, tenant=tenant, landlord=landlord, rent_amount=Decimal('20000'),
        deposit_amount=Decimal('20000'), start_date=date(2026, 1, 1),
        rent_due_day=5, status='active',
    )


@pytest.fixture(autouse=True)
def _clear_throttle_fallback():
    """The in-process fallback limiter must not carry counts from one test into the next."""
    from apps.users.throttling import FALLBACK_CACHE
    FALLBACK_CACHE.clear()
    yield
    FALLBACK_CACHE.clear()
