import os, django, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from decimal import Decimal
from datetime import date
from django.utils import timezone

from apps.users.models import User
from apps.properties.models import Property, Unit
from apps.rentals.models import Lease, Invoice
from apps.payments.models import Payment
from apps.agencies import services as agency_services
from apps.agencies.models import Agency, AgencyRole, PropertyManagementAssignment
from apps.notifications import messaging_services as chat_services
from apps.notifications.messaging_models import MessageThread

print("=== Creating base fixtures ===")
landlord = User.objects.create_user(username='landlord1', email='landlord1@test.com', password='x', role='landlord', phone_number='+254700000001')
agency_admin = User.objects.create_user(username='agencyadmin1', email='agency1@test.com', password='x', role='landlord', phone_number='+254700000002')
tenant = User.objects.create_user(username='tenant1', email='tenant1@test.com', password='x', role='tenant', phone_number='+254700000003')
stranger = User.objects.create_user(username='stranger1', email='stranger1@test.com', password='x', role='tenant', phone_number='+254700000004')

prop = Property.objects.create(landlord=landlord, name='Sunset Apartments', property_type='apartment', county='Nairobi', town='Westlands', address_detail='123 St')
unit = Unit.objects.create(property=prop, unit_number='A1', rent_amount=Decimal('20000'), bedrooms=1, bathrooms=1)

lease = Lease.objects.create(
    unit=unit, tenant=tenant, landlord=landlord, rent_amount=Decimal('20000'), deposit_amount=Decimal('20000'),
    start_date=date(2026, 1, 1), rent_due_day=5, status='active',
)

print("=== Agency creation + staffing ===")
agency = agency_services.create_agency(name='Prime Property Managers', created_by=agency_admin, email='ops@prime.co.ke')
assert agency.roles.count() == 5, "Expected 5 default roles seeded"
print("Agency created:", agency, "| roles:", [r.role_type for r in agency.roles.all()])

print("=== Assign property to agency ===")
assignment = agency_services.assign_property_to_agency(
    property=prop, agency=agency, start_date=date(2026, 1, 1), management_fee_percent=Decimal('10'),
    approved_by=landlord,
)
assert PropertyManagementAssignment.active_for_property(prop) == assignment
print("Active assignment:", assignment)

print("=== Relationship authorization checks ===")
from apps.agencies.permissions import user_can_access_property, properties_visible_to
assert user_can_access_property(landlord, prop) is True
assert user_can_access_property(agency_admin, prop) is True  # agency admin role -> agency-wide access
assert user_can_access_property(tenant, prop) is True  # active lease
assert user_can_access_property(stranger, prop) is False
print("Landlord, agency admin, tenant can access; stranger cannot. OK")

print("=== Record a completed rent payment ===")
invoice = Invoice.objects.create(
    lease=lease, tenant=tenant, invoice_type='rent', amount=Decimal('20000'),
    period_start=date(2026, 1, 1), period_end=date(2026, 1, 31), due_date=date(2026, 1, 5),
)
payment = Payment.objects.create(
    payer=tenant, invoice=invoice, amount=Decimal('20000'), method=Payment.Method.MPESA_STK,
    status=Payment.Status.COMPLETED, completed_at=timezone.make_aware(timezone.datetime(2026, 1, 10)), reference='TESTPAY001',
)

print("=== Generate owner statement ===")
statement = agency_services.generate_owner_statement(
    property=prop, period_start=date(2026, 1, 1), period_end=date(2026, 1, 31), generated_by=agency_admin,
)
print("Statement:", statement.gross_rent_collected, statement.agency_commission, statement.net_payable)
assert statement.gross_rent_collected == Decimal('20000')
assert statement.agency_commission == Decimal('2000.00')
assert statement.net_payable == Decimal('18000.00')

print("=== FRIDAH Chat: relationship-based thread creation ===")
thread, created = chat_services.get_or_create_direct_thread(user=tenant, other_user=agency_admin)
print("Thread created:", created, thread.thread_type)
msg = chat_services.send_message(thread=thread, sender=tenant, body="Hi, is my rent invoice ready?")
print("Message sent:", msg.body)

try:
    chat_services.get_or_create_direct_thread(user=tenant, other_user=stranger)
    print("FAIL: stranger thread should have been rejected")
    sys.exit(1)
except chat_services.RelationshipError as e:
    print("Correctly rejected unrelated thread:", e)

print("=== Share an invoice as a card in chat ===")
msg2 = chat_services.share_object(
    user=agency_admin, thread=thread, obj=invoice, object_type='invoice',
    card_data={'amount': '20000', 'due_date': '2026-01-05'},
)
print("Shared object message type:", msg2.message_type)

print("=== Hotel host <-> guest chat relationship ===")
from apps.bookings.models import Listing, RoomType, Booking

hotel_owner = User.objects.create_user(username='hotel_owner1', email='hotel1@test.com', password='x', role='hotel_owner', phone_number='+254733000001')
guest = User.objects.create_user(username='guest1', email='guest1@test.com', password='x', role='tenant', phone_number='+254733000002')
listing = Listing.objects.create(host=hotel_owner, name='Nairobi Suites', listing_type='hotel', county='Nairobi', town='Westlands')
room_type = RoomType.objects.create(listing=listing, name='Deluxe Room', price_per_night=Decimal('5000'))
booking = Booking.objects.create(
    guest=guest, listing=listing, room_type=room_type, host=hotel_owner,
    check_in_date=date(2026, 2, 1), check_out_date=date(2026, 2, 3), total_amount=Decimal('10000'),
    booking_reference='BK-TEST001',
)
assert chat_services.users_share_relationship(hotel_owner, guest) is True
hotel_thread, created = chat_services.get_or_create_direct_thread(user=guest, other_user=hotel_owner)
assert hotel_thread.thread_type == MessageThread.ThreadType.HOTEL_GUEST
print("Hotel/guest thread created with correct type:", hotel_thread.thread_type)

print("\nALL SMOKE TESTS PASSED")
