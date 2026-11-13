from decimal import Decimal
from datetime import date

import pytest
from django.utils import timezone

from apps.agencies import services as agency_services
from apps.agencies.models import PropertyManagementAssignment, OwnerStatement
from apps.agencies.permissions import user_can_access_property
from apps.rentals.models import Invoice
from apps.payments.models import Payment
from apps.users.models import User


@pytest.mark.django_db
class TestAgencyWorkflow:
    def test_agency_creation_seeds_five_default_roles(self, landlord):
        agency = agency_services.create_agency(name='Prime Property Managers', created_by=landlord, email='ops@prime.co.ke')
        assert agency.roles.count() == 5
        role_types = {r.role_type for r in agency.roles.all()}
        assert role_types == {'agency_admin', 'property_manager', 'caretaker', 'finance_officer', 'leasing_agent'}

    def test_assigning_property_to_agency_creates_active_assignment(self, landlord, property_):
        agency = agency_services.create_agency(name='Prime Property Managers', created_by=landlord, email='ops@prime.co.ke')
        assignment = agency_services.assign_property_to_agency(
            property=property_, agency=agency, start_date=date(2026, 1, 1),
            management_fee_percent=Decimal('10'), approved_by=landlord,
        )
        assert PropertyManagementAssignment.active_for_property(property_) == assignment

    def test_property_access_respects_relationships(self, landlord, tenant, stranger, property_, lease):
        assert user_can_access_property(landlord, property_) is True
        assert user_can_access_property(tenant, property_) is True  # active lease
        assert user_can_access_property(stranger, property_) is False

    def test_owner_statement_math(self, landlord, tenant, property_, lease):
        agency = agency_services.create_agency(name='Prime Property Managers', created_by=landlord, email='ops@prime.co.ke')
        agency_services.assign_property_to_agency(
            property=property_, agency=agency, start_date=date(2026, 1, 1),
            management_fee_percent=Decimal('10'), approved_by=landlord,
        )
        invoice = Invoice.objects.create(
            lease=lease, tenant=tenant, invoice_type='rent', amount=Decimal('20000'),
            period_start=date(2026, 1, 1), period_end=date(2026, 1, 31), due_date=date(2026, 1, 5),
        )
        Payment.objects.create(
            payer=tenant, invoice=invoice, amount=Decimal('20000'), method=Payment.Method.MPESA_STK,
            status=Payment.Status.COMPLETED,
            completed_at=timezone.make_aware(timezone.datetime(2026, 1, 10)),
            reference='TESTPAY001',
        )
        statement = agency_services.generate_owner_statement(
            property=property_, period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
            generated_by=landlord,
        )
        assert statement.gross_rent_collected == Decimal('20000')
        assert statement.agency_commission == Decimal('2000.00')
        assert statement.net_payable == Decimal('18000.00')


@pytest.mark.django_db
class TestAgencyRollupDashboard:
    def _setup_agency_with_property(self, landlord, property_):
        agency = agency_services.create_agency(name='Prime Property Managers', created_by=landlord, email='ops@prime.co.ke')
        agency_services.assign_property_to_agency(
            property=property_, agency=agency, start_date=date(2026, 1, 1),
            management_fee_percent=Decimal('10'), approved_by=landlord,
        )
        return agency

    def test_agency_admin_sees_all_managed_properties(self, api_client, landlord, property_):
        from apps.agencies.models import AgencyMembership
        agency = self._setup_agency_with_property(landlord, property_)
        # create_agency should have made the creating landlord an Agency Admin member
        membership = AgencyMembership.objects.get(agency=agency, user=landlord)
        assert membership.role.role_type == 'agency_admin'

        api_client.force_authenticate(user=landlord)
        resp = api_client.get(f'/api/v1/agencies/{agency.id}/dashboard/')
        assert resp.status_code == 200
        body = resp.data['data']
        assert body['scope'] == 'agency_wide'
        assert body['summary']['total_properties'] == 1

    def test_stranger_cannot_access_agency_dashboard(self, api_client, stranger, landlord, property_):
        agency = self._setup_agency_with_property(landlord, property_)
        api_client.force_authenticate(user=stranger)
        resp = api_client.get(f'/api/v1/agencies/{agency.id}/dashboard/')
        assert resp.status_code == 403

    def test_caretaker_only_sees_assigned_properties(self, api_client, landlord, tenant, property_):
        from apps.agencies.models import AgencyMembership, AgencyRole, PropertyStaffAssignment
        from apps.properties.models import Property
        agency = self._setup_agency_with_property(landlord, property_)

        other_property = Property.objects.create(
            landlord=landlord, name='Other Building', property_type='apartment',
            county='Nairobi', town='Kilimani', address_detail='456 Ave',
        )
        agency_services.assign_property_to_agency(
            property=other_property, agency=agency, start_date=date(2026, 1, 1),
            management_fee_percent=Decimal('10'), approved_by=landlord,
        )

        caretaker_role = AgencyRole.objects.get(agency=agency, role_type=AgencyRole.RoleType.CARETAKER)
        caretaker_membership = AgencyMembership.objects.create(
            agency=agency, user=tenant, role=caretaker_role, status=AgencyMembership.Status.ACTIVE,
        )
        PropertyStaffAssignment.objects.create(
            membership=caretaker_membership, property=property_, is_active=True,
        )

        api_client.force_authenticate(user=tenant)
        resp = api_client.get(f'/api/v1/agencies/{agency.id}/dashboard/')
        assert resp.status_code == 200
        body = resp.data['data']
        assert body['scope'] == 'assigned_properties_only'
        assert body['summary']['total_properties'] == 1
        assert body['properties'][0]['property_id'] == str(property_.id)


@pytest.mark.django_db
class TestAgencyManagesOtherPeoplesProperties:
    """Regression tests: an agency previously could not initiate managing a
    property for a landlord client - it could only sign an agreement the
    landlord had already started, or wait for the landlord/admin to directly
    assign. This is the core value proposition of a property management
    agency, so it being unreachable was a real gap."""

    def test_agency_admin_can_create_property_on_behalf_of_client_landlord(self, api_client, landlord, stranger):
        from apps.agencies import services as agency_services
        agency = agency_services.create_agency(name='Client Onboarding Agency', created_by=landlord, email='ops@onboard.co.ke')

        client_landlord = stranger
        client_landlord.role = 'landlord'
        client_landlord.save()

        api_client.force_authenticate(user=landlord)  # landlord here is the Agency Admin
        resp = api_client.post('/api/v1/properties/', {
            'name': 'Client Building', 'property_type': 'apartment',
            'county': 'Nairobi', 'town': 'Kileleshwa', 'total_units': 5,
            'landlord': str(client_landlord.id),
        }, format='json')
        assert resp.status_code == 201
        from apps.properties.models import Property
        prop = Property.objects.get(id=resp.data['id'])
        assert prop.landlord_id == client_landlord.id

    def test_random_user_still_cannot_create_property_for_someone_else(self, api_client, stranger, landlord):
        """Confirms the fix is scoped to agency staff, not opened up to everyone.
        stranger has role='tenant' so IsLandlordOrAdmin blocks them at 403 before
        even reaching the serializer's landlord validation."""
        api_client.force_authenticate(user=stranger)
        resp = api_client.post('/api/v1/properties/', {
            'name': 'Sneaky Building', 'property_type': 'apartment',
            'county': 'Nairobi', 'town': 'Kileleshwa', 'total_units': 5,
            'landlord': str(landlord.id),
        }, format='json')
        assert resp.status_code == 403

    def test_landlord_without_agency_membership_cannot_create_for_another_landlord(self, api_client, landlord, property_):
        """A plain landlord (role='landlord', passes IsLandlordOrAdmin) with no
        agency membership still can't create a property for a DIFFERENT landlord -
        the serializer-level check must still gate this."""
        from apps.users.models import User
        other_landlord = User.objects.create_user(
            username='other_ll_gap', email='other_ll_gap@test.com', password='x',
            role='landlord', phone_number='+254700555099',
        )
        api_client.force_authenticate(user=other_landlord)
        resp = api_client.post('/api/v1/properties/', {
            'name': 'Sneaky Building 2', 'property_type': 'apartment',
            'county': 'Nairobi', 'town': 'Kileleshwa', 'total_units': 5,
            'landlord': str(landlord.id),
        }, format='json')
        assert resp.status_code == 400

    def test_agency_admin_can_propose_management_agreement_for_client_property(self, api_client, landlord, property_):
        """property_ fixture is owned by `landlord`, who is NOT the agency creator here -
        simulating an agency proposing to manage a property for a genuine client."""
        from apps.agencies import services as agency_services
        from apps.users.models import User

        agency_owner = User.objects.create_user(
            username='agency_owner1', email='agency_owner1@test.com', password='x',
            role='landlord', phone_number='+254700555001',
        )
        agency = agency_services.create_agency(name='Proposing Agency', created_by=agency_owner, email='ops@proposing.co.ke')

        api_client.force_authenticate(user=agency_owner)
        resp = api_client.post('/api/v1/agency/agreements/', {
            'property': str(property_.id), 'agency': str(agency.id),
            'management_fee_percent': '8.00', 'start_date': '2026-03-01',
        }, format='json')
        assert resp.status_code == 201
        # ManagementAgreementListCreateView is a plain generics.ListCreateAPIView,
        # so - like PropertyListCreateView elsewhere in the API - it returns raw
        # serializer data, not the app's {success, data} envelope.
        assert resp.data['status'] == 'pending_signatures'
        assert resp.data['owner'] == property_.landlord_id  # forced to the REAL owner, not the agency

    def test_agreement_only_becomes_active_after_owner_signs_not_just_agency(self, api_client, landlord, property_):
        """The consent safeguard: an agency proposing an agreement cannot make it
        ACTIVE by itself - the actual property owner must separately sign."""
        from apps.agencies import services as agency_services
        from apps.agencies.models import ManagementAgreement
        from apps.users.models import User

        agency_owner = User.objects.create_user(
            username='agency_owner2', email='agency_owner2@test.com', password='x',
            role='landlord', phone_number='+254700555002',
        )
        agency = agency_services.create_agency(name='Consent Test Agency', created_by=agency_owner, email='ops@consent.co.ke')

        api_client.force_authenticate(user=agency_owner)
        create_resp = api_client.post('/api/v1/agency/agreements/', {
            'property': str(property_.id), 'agency': str(agency.id),
            'management_fee_percent': '8.00', 'start_date': '2026-03-01',
        }, format='json')
        agreement_id = create_resp.data['id']

        # agency signs its side
        api_client.post(f'/api/v1/agency/agreements/{agreement_id}/sign/', {'as': 'agency'}, format='json')
        agreement = ManagementAgreement.objects.get(id=agreement_id)
        assert agreement.status == ManagementAgreement.Status.PENDING_SIGNATURES  # still pending - owner hasn't signed

        # now the real owner signs
        api_client.force_authenticate(user=landlord)
        api_client.post(f'/api/v1/agency/agreements/{agreement_id}/sign/', {'as': 'owner'}, format='json')
        agreement.refresh_from_db()
        assert agreement.status == ManagementAgreement.Status.ACTIVE

    def test_stranger_agency_cannot_propose_agreement_without_membership(self, api_client, stranger, landlord, property_):
        """A user with no active membership in the named agency can't use it to
        propose an agreement - has_agency_permission must actually gate this."""
        from apps.agencies import services as agency_services
        from apps.users.models import User

        real_agency_owner = User.objects.create_user(
            username='real_agency_owner', email='real_agency_owner@test.com', password='x',
            role='landlord', phone_number='+254700555003',
        )
        agency = agency_services.create_agency(name='Real Owners Agency', created_by=real_agency_owner, email='ops@real.co.ke')

        api_client.force_authenticate(user=stranger)
        resp = api_client.post('/api/v1/agency/agreements/', {
            'property': str(property_.id), 'agency': str(agency.id),
            'management_fee_percent': '8.00', 'start_date': '2026-03-01',
        }, format='json')
        assert resp.status_code == 403


class TestOwnerVisibilityIntoAgencyManagedProperties:
    """
    A landlord should be able to see the actual management terms (fee %, payout rule,
    since when, agreement status) for a property an agency manages on their behalf, and
    should be able to view/list statements and payouts for their own properties - but
    never anyone else's.
    """

    def _setup_agency_with_property(self, landlord, property_, fee_percent=Decimal('10')):
        agency = agency_services.create_agency(name='Prime Property Managers', created_by=landlord, email='ops@prime.co.ke')
        agency_services.assign_property_to_agency(
            property=property_, agency=agency, start_date=date(2026, 1, 1),
            management_fee_percent=fee_percent, approved_by=landlord,
        )
        return agency

    def test_owner_properties_endpoint_includes_management_terms(self, api_client, landlord, property_):
        self._setup_agency_with_property(landlord, property_, fee_percent=Decimal('12.5'))

        api_client.force_authenticate(user=landlord)
        resp = api_client.get('/api/v1/owner/properties/')

        assert resp.status_code == 200
        row = next(r for r in resp.data['data'] if r['id'] == str(property_.id))
        assert row['self_managed'] is False
        assert row['managing_agency']['name'] == 'Prime Property Managers'
        assert row['managing_agency']['management_fee_percent'] == '12.50'
        assert row['managing_agency']['payout_rule'] == 'owner_direct'
        assert row['managing_agency']['managed_since'] == '2026-01-01'

    def test_owner_can_view_own_statement(self, api_client, landlord, property_):
        agency = self._setup_agency_with_property(landlord, property_)
        statement = OwnerStatement.objects.create(
            property=property_, agency=agency, owner=landlord,
            period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
            gross_rent_collected=Decimal('50000'), agency_commission=Decimal('5000'),
        )
        statement.recompute_net()
        statement.save()

        api_client.force_authenticate(user=landlord)
        resp = api_client.get(f'/api/v1/agency/statements/{statement.id}/')
        assert resp.status_code == 200
        assert Decimal(resp.data['net_payable']) == Decimal('45000.00')

    def test_stranger_cannot_view_someone_elses_statement_by_id(self, api_client, stranger, landlord, property_):
        """
        Regression test: OwnerStatementDetailView previously had no queryset scoping at
        all (`queryset = OwnerStatement.objects.all()`), so any authenticated user could
        fetch any owner's financial statement - gross rent, commission, net payable, PDF
        link - just by guessing/enumerating a UUID. This must 404, not 200.
        """
        agency = self._setup_agency_with_property(landlord, property_)
        statement = OwnerStatement.objects.create(
            property=property_, agency=agency, owner=landlord,
            period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
            gross_rent_collected=Decimal('50000'), agency_commission=Decimal('5000'),
        )

        api_client.force_authenticate(user=stranger)
        resp = api_client.get(f'/api/v1/agency/statements/{statement.id}/')
        assert resp.status_code == 404

    def test_stranger_landlord_does_not_see_statement_in_their_list(self, api_client, stranger, landlord, property_):
        agency = self._setup_agency_with_property(landlord, property_)
        OwnerStatement.objects.create(
            property=property_, agency=agency, owner=landlord,
            period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
            gross_rent_collected=Decimal('50000'),
        )

        api_client.force_authenticate(user=stranger)
        resp = api_client.get('/api/v1/agency/statements/')
        assert resp.status_code == 200
        assert resp.data['results'] == []


class TestListingAgencyManagement:
    """
    The hotel/short-stay equivalent of the rental agency-management flow: a host can
    assign one of their listings to an agency, the agency can generate a revenue
    statement from actual checked-out bookings, and the host (whatever their base
    User.role is - hotel_owner here) can see it - exactly mirroring what already works
    for a landlord's Property, but for a Listing instead.
    """

    def _hotel_owner(self):
        return User.objects.create_user(
            username='hotelowner1', email='hotelowner1@test.com', password='StrongPass123!',
            role='hotel_owner', phone_number='+254700000010',
        )

    def _listing(self, host):
        from apps.bookings.models import Listing
        return Listing.objects.create(
            host=host, name='Nairobi Boutique Hotel', listing_type='hotel', status='active',
            county='Nairobi', town='Westlands',
        )

    def _room_type(self, listing, price=Decimal('5000'), rooms=2):
        from apps.bookings.models import RoomType
        return RoomType.objects.create(
            listing=listing, name='Standard Room', price_per_night=price, total_rooms=rooms,
        )

    def _checked_out_booking(self, listing, room_type, guest, check_in, check_out, amount_paid):
        from apps.bookings.models import Booking
        return Booking.objects.create(
            guest=guest, listing=listing, room_type=room_type, host=listing.host,
            check_in_date=check_in, check_out_date=check_out, num_guests=1, num_rooms=1,
            total_amount=amount_paid, amount_paid=amount_paid, status=Booking.Status.CHECKED_OUT,
        )

    def test_host_can_assign_listing_to_agency(self, api_client, landlord, tenant):
        host = self._hotel_owner()
        listing = self._listing(host)
        agency = agency_services.create_agency(name='Nairobi Hospitality Group', created_by=landlord, email='ops@nhg.co.ke')

        api_client.force_authenticate(user=host)
        resp = api_client.post('/api/v1/agency/assignments/assign-listing/', {
            'listing_id': str(listing.id), 'agency_id': str(agency.id),
            'start_date': '2026-01-01', 'management_fee_percent': 15,
        })
        assert resp.status_code == 201
        assert str(resp.data['data']['listing']) == str(listing.id)
        assert resp.data['data']['property'] is None
        assert resp.data['data']['listing_name'] == 'Nairobi Boutique Hotel'
        assert resp.data['data']['management_fee_percent'] == '15.00'

    def test_stranger_cannot_assign_someone_elses_listing(self, api_client, landlord, stranger):
        host = self._hotel_owner()
        listing = self._listing(host)
        agency = agency_services.create_agency(name='Nairobi Hospitality Group', created_by=landlord, email='ops@nhg.co.ke')

        api_client.force_authenticate(user=stranger)
        resp = api_client.post('/api/v1/agency/assignments/assign-listing/', {
            'listing_id': str(listing.id), 'agency_id': str(agency.id), 'start_date': '2026-01-01',
        })
        assert resp.status_code == 403

    def test_owner_listings_endpoint_includes_management_terms(self, api_client, landlord):
        host = self._hotel_owner()
        listing = self._listing(host)
        agency = agency_services.create_agency(name='Nairobi Hospitality Group', created_by=landlord, email='ops@nhg.co.ke')
        agency_services.assign_listing_to_agency(
            listing=listing, agency=agency, start_date=date(2026, 1, 1),
            management_fee_percent=Decimal('12'), approved_by=host,
        )

        api_client.force_authenticate(user=host)
        resp = api_client.get('/api/v1/owner/listings/')
        assert resp.status_code == 200
        row = next(r for r in resp.data['data'] if r['id'] == str(listing.id))
        assert row['self_managed'] is False
        assert row['managing_agency']['name'] == 'Nairobi Hospitality Group'
        assert row['managing_agency']['management_fee_percent'] == '12.00'

    def test_generate_listing_statement_from_checked_out_bookings(self, api_client, landlord, tenant):
        host = self._hotel_owner()
        listing = self._listing(host)
        room_type = self._room_type(listing)
        agency = agency_services.create_agency(name='Nairobi Hospitality Group', created_by=landlord, email='ops@nhg.co.ke')
        agency_services.assign_listing_to_agency(
            listing=listing, agency=agency, start_date=date(2026, 1, 1),
            management_fee_percent=Decimal('10'), approved_by=host,
        )
        # Checked-out within January - counts
        self._checked_out_booking(listing, room_type, tenant, date(2026, 1, 5), date(2026, 1, 8), Decimal('15000'))
        # Checked-out in February - must NOT count toward the January statement
        self._checked_out_booking(listing, room_type, tenant, date(2026, 2, 1), date(2026, 2, 3), Decimal('10000'))

        api_client.force_authenticate(user=landlord)
        resp = api_client.post('/api/v1/agency/statements/generate-listing/', {
            'listing_id': str(listing.id), 'period_start': '2026-01-01', 'period_end': '2026-01-31',
        })
        assert resp.status_code == 200
        data = resp.data['data']
        assert Decimal(data['gross_rent_collected']) == Decimal('15000.00')
        assert Decimal(data['agency_commission']) == Decimal('1500.00')
        assert Decimal(data['net_payable']) == Decimal('13500.00')
        assert str(data['listing']) == str(listing.id)
        assert data['property'] is None

    def test_hotel_owner_sees_their_own_statement(self, api_client, landlord, tenant):
        host = self._hotel_owner()
        listing = self._listing(host)
        agency = agency_services.create_agency(name='Nairobi Hospitality Group', created_by=landlord, email='ops@nhg.co.ke')
        agency_services.assign_listing_to_agency(
            listing=listing, agency=agency, start_date=date(2026, 1, 1), approved_by=host,
        )
        statement = agency_services.generate_owner_statement_for_listing(
            listing=listing, period_start=date(2026, 1, 1), period_end=date(2026, 1, 31), generated_by=host,
        )

        api_client.force_authenticate(user=host)
        resp = api_client.get('/api/v1/agency/statements/')
        assert resp.status_code == 200
        assert any(s['id'] == str(statement.id) for s in resp.data['results'])

        detail_resp = api_client.get(f'/api/v1/agency/statements/{statement.id}/')
        assert detail_resp.status_code == 200
        assert detail_resp.data['listing_name'] == 'Nairobi Boutique Hotel'

    def test_stranger_cannot_view_hotel_owners_statement(self, api_client, landlord, stranger, tenant):
        host = self._hotel_owner()
        listing = self._listing(host)
        statement = agency_services.generate_owner_statement_for_listing(
            listing=listing, period_start=date(2026, 1, 1), period_end=date(2026, 1, 31), generated_by=host,
        )

        api_client.force_authenticate(user=stranger)
        resp = api_client.get(f'/api/v1/agency/statements/{statement.id}/')
        assert resp.status_code == 404

    def test_hotel_owner_sees_payout_for_their_statement(self, api_client, landlord, tenant):
        host = self._hotel_owner()
        listing = self._listing(host)
        room_type = self._room_type(listing)
        self._checked_out_booking(listing, room_type, tenant, date(2026, 1, 5), date(2026, 1, 8), Decimal('20000'))
        statement = agency_services.generate_owner_statement_for_listing(
            listing=listing, period_start=date(2026, 1, 1), period_end=date(2026, 1, 31), generated_by=host,
        )
        agency_services.issue_statement(statement, issued_by=host)
        agency_services.execute_owner_payout(statement, initiated_by=host, phone_number='+254700000010')

        api_client.force_authenticate(user=host)
        resp = api_client.get('/api/v1/agency/payouts/')
        assert resp.status_code == 200
        assert any(str(p['statement']) == str(statement.id) for p in resp.data['results'])

    def test_property_and_listing_statements_can_share_a_period_without_colliding(self, api_client, landlord, property_, tenant):
        """Regression check for the two separate UniqueConstraints (property+period,
        listing+period) replacing the old single unique_together('property', ...)."""
        host = self._hotel_owner()
        listing = self._listing(host)

        prop_statement = agency_services.generate_owner_statement(
            property=property_, period_start=date(2026, 1, 1), period_end=date(2026, 1, 31), generated_by=landlord,
        )
        listing_statement = agency_services.generate_owner_statement_for_listing(
            listing=listing, period_start=date(2026, 1, 1), period_end=date(2026, 1, 31), generated_by=host,
        )
        assert prop_statement.id != listing_statement.id
        assert prop_statement.property_id == property_.id and prop_statement.listing_id is None
        assert listing_statement.listing_id == listing.id and listing_statement.property_id is None


class TestOwnerPortfolioAndAgencyOwnerVisibility:
    """
    The landlord must be able to see - in one place - which of their properties an agency
    manages, who is living there, and the revenue collected; and the agency must be able to
    see who actually owns each property it manages.
    """

    def _agency_managed(self, landlord, property_, fee='10'):
        agency = agency_services.create_agency(name='Prime Managers', created_by=landlord, email='ops@prime.co.ke')
        agency_services.assign_property_to_agency(
            property=property_, agency=agency, start_date=date(2026, 1, 1),
            management_fee_percent=Decimal(fee), approved_by=landlord,
        )
        return agency

    def test_portfolio_shows_agency_tenants_and_revenue(self, api_client, landlord, property_, lease, tenant):
        self._agency_managed(landlord, property_, fee='10')
        invoice = Invoice.objects.create(
            lease=lease, tenant=tenant, invoice_type='rent', amount=Decimal('20000'),
            period_start=date(2026, 1, 1), period_end=date(2026, 1, 31), due_date=date(2026, 1, 5),
        )
        Payment.objects.create(
            payer=tenant, invoice=invoice, amount=Decimal('20000'), method=Payment.Method.MPESA_STK,
            status=Payment.Status.COMPLETED,
            completed_at=timezone.make_aware(timezone.datetime(2026, 1, 10)), reference='PORTFOLIO001',
        )

        api_client.force_authenticate(user=landlord)
        resp = api_client.get('/api/v1/owner/portfolio/?period_start=2026-01-01&period_end=2026-01-31')
        assert resp.status_code == 200
        data = resp.data['data']
        row = next(r for r in data['properties'] if r['id'] == str(property_.id))

        assert row['self_managed'] is False
        assert row['managed_by']['name'] == 'Prime Managers'
        assert row['occupied_units'] == 1
        assert row['tenants'][0]['unit'] == 'A1'
        assert Decimal(row['revenue_collected']) == Decimal('20000')
        assert Decimal(row['agency_fee']) == Decimal('2000.00')
        assert Decimal(row['net_to_owner']) == Decimal('18000.00')
        assert Decimal(data['totals']['revenue_collected']) == Decimal('20000')
        assert data['totals']['agency_managed'] == 1

    def test_portfolio_period_excludes_other_months(self, api_client, landlord, property_, lease, tenant):
        invoice = Invoice.objects.create(
            lease=lease, tenant=tenant, invoice_type='rent', amount=Decimal('20000'),
            period_start=date(2026, 2, 1), period_end=date(2026, 2, 28), due_date=date(2026, 2, 5),
        )
        Payment.objects.create(
            payer=tenant, invoice=invoice, amount=Decimal('20000'), method=Payment.Method.MPESA_STK,
            status=Payment.Status.COMPLETED,
            completed_at=timezone.make_aware(timezone.datetime(2026, 2, 10)), reference='PORTFOLIO002',
        )
        api_client.force_authenticate(user=landlord)
        resp = api_client.get('/api/v1/owner/portfolio/?period_start=2026-01-01&period_end=2026-01-31')
        assert Decimal(resp.data['data']['totals']['revenue_collected']) == Decimal('0')

    def test_portfolio_never_shows_someone_elses_properties(self, api_client, landlord, stranger, property_, lease):
        self._agency_managed(landlord, property_)
        api_client.force_authenticate(user=stranger)
        resp = api_client.get('/api/v1/owner/portfolio/')
        assert resp.status_code == 200
        assert resp.data['data']['properties'] == []
        assert resp.data['data']['listings'] == []

    def test_agency_sees_who_owns_the_property(self, api_client, landlord, property_):
        agency = self._agency_managed(landlord, property_)
        api_client.force_authenticate(user=landlord)  # landlord is also the agency admin in this fixture
        resp = api_client.get(f'/api/v1/agency/assignments/?agency={agency.id}')
        assert resp.status_code == 200
        row = resp.data['results'][0]
        assert row['owner_email'] == landlord.email
        assert row['owner_phone'] == landlord.phone_number
        assert row['owner_name']
        assert row['item_type'] == 'property'
        assert row['location']
