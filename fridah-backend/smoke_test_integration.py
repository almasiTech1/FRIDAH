import os, django, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')

from decimal import Decimal
from datetime import date
from rest_framework.test import APIClient

from apps.users.models import User
from apps.properties.models import Property, Unit
from apps.rentals.models import Lease, MaintenanceRequest
from apps.agencies import services as agency_services

print("=== Fixtures ===")
landlord = User.objects.create_user(username='int_landlord', email='int_landlord@test.com', password='x', role='landlord', phone_number='+254722000001')
agency_staff = User.objects.create_user(username='int_staff', email='int_staff@test.com', password='x', role='landlord', phone_number='+254722000002')
tenant = User.objects.create_user(username='int_tenant', email='int_tenant@test.com', password='x', role='tenant', phone_number='+254722000003')
outsider = User.objects.create_user(username='int_outsider', email='int_outsider@test.com', password='x', role='landlord', phone_number='+254722000004')

prop = Property.objects.create(landlord=landlord, name='Integration Towers', property_type='apartment', county='Nairobi', town='CBD', address_detail='1 Main St')
unit = Unit.objects.create(property=prop, unit_number='C1', rent_amount=Decimal('30000'), bedrooms=2, bathrooms=1)
lease = Lease.objects.create(unit=unit, tenant=tenant, landlord=landlord, rent_amount=Decimal('30000'), deposit_amount=Decimal('30000'), start_date=date(2026, 1, 1), rent_due_day=5, status='active')
maint = MaintenanceRequest.objects.create(tenant=tenant, unit=unit, title='Broken window', description='Window latch broken', category='general', priority='medium')

agency = agency_services.create_agency(name='Integration PM Co', created_by=agency_staff)
membership = agency.memberships.get(user=agency_staff)
property_manager_role = agency.roles.get(role_type='property_manager')
membership.role = property_manager_role
membership.save()
agency_services.assign_property_to_agency(property=prop, agency=agency, start_date=date(2026, 1, 1), approved_by=landlord)
agency_services.assign_staff_to_property(property=prop, membership=membership, assigned_by=landlord)

client = APIClient()

print("=== Agency staff can see the property via GET /properties/ ===")
client.force_authenticate(user=agency_staff)
resp = client.get('/api/v1/properties/')
results = resp.data['results'] if 'results' in resp.data else resp.data
ids = [p['id'] for p in results]
print("Status:", resp.status_code, "| Properties visible:", len(ids))
assert resp.status_code == 200
assert str(prop.id) in ids, f"Agency staff should see managed property; got {ids}"

print("=== Agency staff (property_manager) can update the property ===")
resp = client.patch(f'/api/v1/properties/{prop.id}/', {'description': 'Freshly renovated 2BR units'}, format='json')
print("Status:", resp.status_code)
assert resp.status_code in (200, 202), resp.data

print("=== Outsider landlord CANNOT update the property ===")
client.force_authenticate(user=outsider)
resp = client.patch(f'/api/v1/properties/{prop.id}/', {'description': 'Hijacked!'}, format='json')
print("Status:", resp.status_code)
assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.data}"

print("=== Agency staff can add a unit to the managed property ===")
client.force_authenticate(user=agency_staff)
resp = client.post(f'/api/v1/properties/{prop.id}/units/', {
    'property': str(prop.id), 'unit_number': 'C2', 'rent_amount': '32000', 'bedrooms': 2, 'bathrooms': 1,
}, format='json')
print("Status:", resp.status_code)
assert resp.status_code == 201, resp.data

print("=== Outsider CANNOT add a unit ===")
client.force_authenticate(user=outsider)
resp = client.post(f'/api/v1/properties/{prop.id}/units/', {
    'property': str(prop.id), 'unit_number': 'C3', 'rent_amount': '32000', 'bedrooms': 2, 'bathrooms': 1,
}, format='json')
print("Status:", resp.status_code)
assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.data}"

print("=== Agency staff (property_manager) can assign a maintenance provider ===")
provider = User.objects.create_user(username='int_provider', email='int_provider@test.com', password='x', role='service_provider', phone_number='+254722000005')
client.force_authenticate(user=agency_staff)
resp = client.post(f'/api/v1/maintenance/{maint.id}/assign/', {'provider_id': str(provider.id)}, format='json')
print("Status:", resp.status_code)
assert resp.status_code == 200, resp.data

print("=== Tenant can view their own lease; outsider cannot ===")
client.force_authenticate(user=tenant)
resp = client.get(f'/api/v1/leases/{lease.id}/')
assert resp.status_code == 200
client.force_authenticate(user=outsider)
resp = client.get(f'/api/v1/leases/{lease.id}/')
print("Outsider lease access status:", resp.status_code)
assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.data}"

print("=== Management assignment history: scoped access ===")
client.force_authenticate(user=landlord)
resp = client.get(f'/api/v1/agency/assignments/?property={prop.id}')
landlord_results = resp.data['results'] if 'results' in resp.data else resp.data
print("Landlord (owner) status:", resp.status_code, "| count:", len(landlord_results))
assert resp.status_code == 200 and len(landlord_results) >= 1

client.force_authenticate(user=outsider)
resp = client.get(f'/api/v1/agency/assignments/?property={prop.id}')
outsider_results = resp.data['results'] if 'results' in resp.data else resp.data
print("Outsider status:", resp.status_code, "| count:", len(outsider_results))
assert resp.status_code == 200 and len(outsider_results) == 0, "Outsider should not see this property's assignment history"

print("=== Agency directory search ===")
agency.status = agency.Status.ACTIVE
agency.save(update_fields=['status'])
resp = client.get('/api/v1/agencies/directory/?search=Integration')
results = resp.data['data'] if 'data' in resp.data else resp.data
print("Status:", resp.status_code, "| Results:", [r['name'] for r in results])
assert resp.status_code == 200
assert any(r['name'] == 'Integration PM Co' for r in results)
assert 'default_fee_percent' not in results[0], "Directory search should not leak internal fee settings"

print("\nALL INTEGRATION SMOKE TESTS PASSED")
