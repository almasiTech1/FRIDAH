from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from decimal import Decimal

from apps.users.permissions import IsLandlordOrAdmin, IsAdminRole
from apps.properties.models import Property
from apps.bookings.models import Listing

from .models import (
    Agency, AgencyRole, AgencyMembership, PropertyManagementAssignment, PropertyStaffAssignment,
    AgencyFeeRule, ManagementAgreement, OwnerStatement, OwnerPayout, AgencyCommission,
    AgencyExpense, AgencyAuditLog,
)
from .serializers import (
    AgencyRegistrationSerializer,
    AgencySerializer, AgencyDirectorySerializer, AgencyRoleSerializer, AgencyMembershipSerializer, InviteStaffSerializer,
    PropertyStaffAssignmentSerializer, AgencyFeeRuleSerializer, ManagementAgreementSerializer,
    PropertyManagementAssignmentSerializer, AssignPropertySerializer, AssignListingSerializer, OwnerStatementSerializer,
    GenerateStatementSerializer, GenerateListingStatementSerializer, OwnerPayoutSerializer, AgencyCommissionSerializer,
    AgencyExpenseSerializer, AgencyAuditLogSerializer,
)
from .permissions import agency_membership_for, agencies_staffed_by, has_agency_permission, properties_visible_to
from . import services


def success(data=None, message="OK", status_code=status.HTTP_200_OK):
    return Response({'success': True, 'message': message, 'data': data}, status=status_code)


def error(message, status_code=status.HTTP_400_BAD_REQUEST):
    return Response({'success': False, 'error': {'message': message}}, status=status_code)


def _require_agency_permission(request, agency, code):
    if request.user.role == 'admin' or request.user.is_staff:
        return
    if not has_agency_permission(request.user, agency, code):
        raise PermissionDenied(f"You do not have '{code}' permission in this agency.")


class AgencyDirectorySearchView(generics.ListAPIView):
    """
    Public-within-platform search so a property owner can find an agency to assign
    their property to without needing to already know its ID. Only surfaces active
    agencies and limited, non-sensitive fields (see AgencyDirectorySerializer).
    """
    serializer_class = AgencyDirectorySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        qs = Agency.objects.filter(status=Agency.Status.ACTIVE)
        search = self.request.query_params.get('search', '').strip()
        if search:
            from django.db.models import Q
            qs = qs.filter(Q(name__icontains=search) | Q(town__icontains=search) | Q(county__icontains=search))
        return qs.order_by('name')[:20]


class AgencyListCreateView(generics.ListCreateAPIView):
    serializer_class = AgencySerializer

    def get_permissions(self):
        # Registering an agency company is an administrator-only action. Tenants, landlords,
        # service providers and hotel owners cannot create one for themselves.
        if self.request.method == 'POST':
            return [IsAdminRole()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        return AgencyRegistrationSerializer if self.request.method == 'POST' else AgencySerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin' or user.is_staff:
            return Agency.objects.all().order_by('name')
        return agencies_staffed_by(user).order_by('name')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        agency, agency_admin, temp_password = services.register_agency(
            registered_by=request.user, **serializer.validated_data,
        )
        data = AgencyRegistrationSerializer(agency).data
        # Shown ONCE so the administrator can hand it over; it is never stored or retrievable.
        data['credentials'] = {
            'login_email': agency_admin.email, 'temporary_password': temp_password,
            'must_change_on_first_login': True,
        }
        return success(data, message="Agency registered.", status_code=status.HTTP_201_CREATED)


class AgencyResetAdminPasswordView(APIView):
    """Admin: issue a new temporary password to an agency's Agency Admin (no self-service reset exists)."""
    permission_classes = [IsAdminRole]

    def post(self, request, id):
        agency = get_object_or_404(Agency, id=id)
        try:
            user, temp_password = services.reset_agency_admin_password(agency=agency, admin=request.user)
        except ValueError as e:
            return error(str(e), status.HTTP_400_BAD_REQUEST)
        return success({'login_email': user.email, 'temporary_password': temp_password,
                        'must_change_on_first_login': True}, message="Temporary password issued.")


class AgencyStatusView(APIView):
    """Admin: activate / suspend / archive an agency. POST {status}."""
    permission_classes = [IsAdminRole]

    def post(self, request, id):
        agency = get_object_or_404(Agency, id=id)
        try:
            services.set_agency_status(agency=agency, admin=request.user, status=request.data.get('status'))
        except ValueError as e:
            return error(str(e), status.HTTP_400_BAD_REQUEST)
        return success({'status': agency.status}, message="Agency status updated.")


class AgencyDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = AgencySerializer
    queryset = Agency.objects.all()
    lookup_field = 'id'

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def update(self, request, *args, **kwargs):
        agency = self.get_object()
        _require_agency_permission(request, agency, 'agency.manage_settings')
        return super().update(request, *args, **kwargs)


class AgencyRoleListCreateView(generics.ListCreateAPIView):
    serializer_class = AgencyRoleSerializer

    def get_queryset(self):
        return AgencyRole.objects.filter(agency_id=self.kwargs['agency_id'])

    def perform_create(self, serializer):
        agency = get_object_or_404(Agency, id=self.kwargs['agency_id'])
        _require_agency_permission(self.request, agency, 'agency.manage_staff')
        serializer.save(agency=agency, role_type=AgencyRole.RoleType.CUSTOM)


class AgencyMembershipListView(generics.ListAPIView):
    serializer_class = AgencyMembershipSerializer
    filterset_fields = ['status']

    def get_queryset(self):
        return AgencyMembership.objects.filter(agency_id=self.kwargs['agency_id']).select_related('user', 'role')


class InviteStaffView(APIView):
    def post(self, request, agency_id):
        agency = get_object_or_404(Agency, id=agency_id)
        _require_agency_permission(request, agency, 'agency.manage_staff')

        serializer = InviteStaffSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from apps.users.models import User
        data = serializer.validated_data
        role = get_object_or_404(AgencyRole, id=data['role_id'], agency=agency)
        user = User.objects.filter(email__iexact=data['email']).first()

        if user is not None:
            membership = services.invite_staff(agency=agency, invited_by=request.user, user=user, role=role)
            return success(AgencyMembershipSerializer(membership).data, message="Invitation sent.",
                           status_code=status.HTTP_201_CREATED)

        # No account yet: the agency creates the login itself (nobody self-registers).
        missing = {f: 'Required to create a login for a new staff member.'
                   for f in ('first_name', 'last_name', 'phone_number') if not (data.get(f) or '').strip()}
        if missing:
            return Response(missing, status=status.HTTP_400_BAD_REQUEST)
        phone = data['phone_number'].strip()
        try:
            for v in User._meta.get_field('phone_number').validators:
                v(phone)
        except Exception as e:
            return Response({'phone_number': list(getattr(e, 'messages', [str(e)]))}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(phone_number=phone).exists():
            return Response({'phone_number': ['An account with this phone number already exists.']},
                            status=status.HTTP_400_BAD_REQUEST)
        membership, temp_password = services.create_staff_account(
            agency=agency, created_by=request.user, role=role, first_name=data['first_name'],
            last_name=data['last_name'], email=data['email'], phone_number=phone,
        )
        out = AgencyMembershipSerializer(membership).data
        out['credentials'] = {'login_email': membership.user.email, 'temporary_password': temp_password,
                              'must_change_on_first_login': True}
        return success(out, message="Staff login created.", status_code=status.HTTP_201_CREATED)


class StaffResetPasswordView(APIView):
    """Agency admin (or anyone with manage-staff): issue a new temporary password to a staff member."""

    def post(self, request, membership_id):
        membership = get_object_or_404(AgencyMembership.objects.select_related('user', 'agency', 'role'), id=membership_id)
        _require_agency_permission(request, membership.agency, 'agency.manage_staff')
        if membership.user_id == request.user.id:
            return error("Change your own password from your profile.")
        if membership.role.role_type == 'agency_admin' and not (request.user.role == 'admin' or request.user.is_staff):
            return error("Only a platform administrator can reset an Agency Admin's login.", status.HTTP_403_FORBIDDEN)
        temp_password = services.reset_staff_password(membership=membership, reset_by=request.user)
        return success({'login_email': membership.user.email, 'temporary_password': temp_password,
                        'must_change_on_first_login': True}, message="Temporary password issued.")


class AcceptInviteView(APIView):
    def post(self, request, membership_id):
        membership = get_object_or_404(AgencyMembership, id=membership_id, user=request.user)
        if membership.status != AgencyMembership.Status.INVITED:
            return error("This invitation is no longer pending.")
        services.accept_invite(membership)
        return success(AgencyMembershipSerializer(membership).data, message="Welcome to the agency.")


class MembershipSuspendView(APIView):
    def post(self, request, membership_id):
        membership = get_object_or_404(AgencyMembership, id=membership_id)
        _require_agency_permission(request, membership.agency, 'agency.manage_staff')
        membership.status = AgencyMembership.Status.SUSPENDED
        membership.save(update_fields=['status'])
        services.log_audit(membership.agency, request.user, 'staff.suspended', target=membership)
        return success(message="Membership suspended.")


class MembershipRemoveView(APIView):
    def post(self, request, membership_id):
        membership = get_object_or_404(AgencyMembership, id=membership_id)
        _require_agency_permission(request, membership.agency, 'agency.manage_staff')
        membership.status = AgencyMembership.Status.REMOVED
        membership.removed_at = timezone.now()
        membership.save(update_fields=['status', 'removed_at'])
        PropertyStaffAssignment.objects.filter(membership=membership, is_active=True).update(
            is_active=False, removed_at=timezone.now()
        )
        services.log_audit(membership.agency, request.user, 'staff.removed', target=membership)
        return success(message="Membership removed.")


class PropertyStaffAssignmentListCreateView(generics.ListCreateAPIView):
    serializer_class = PropertyStaffAssignmentSerializer

    def get_queryset(self):
        qs = PropertyStaffAssignment.objects.select_related('property', 'membership__user')
        property_id = self.request.query_params.get('property')
        if property_id:
            qs = qs.filter(property_id=property_id)
        return qs

    def create(self, request, *args, **kwargs):
        property = get_object_or_404(Property, id=request.data.get('property'))
        membership = get_object_or_404(AgencyMembership, id=request.data.get('membership'))
        _require_agency_permission(request, membership.agency, 'agency.manage_staff')
        assignment = services.assign_staff_to_property(property=property, membership=membership, assigned_by=request.user)
        return success(
            PropertyStaffAssignmentSerializer(assignment).data, message="Staff assigned to property.",
            status_code=status.HTTP_201_CREATED,
        )


class PropertyStaffAssignmentRemoveView(APIView):
    def post(self, request, id):
        assignment = get_object_or_404(PropertyStaffAssignment, id=id)
        _require_agency_permission(request, assignment.membership.agency, 'agency.manage_staff')
        services.remove_staff_from_property(assignment, removed_by=request.user)
        return success(message="Staff removed from property.")


class AgencyFeeRuleListCreateView(generics.ListCreateAPIView):
    serializer_class = AgencyFeeRuleSerializer

    def get_queryset(self):
        return AgencyFeeRule.objects.filter(agency_id=self.kwargs['agency_id'])

    def perform_create(self, serializer):
        agency = get_object_or_404(Agency, id=self.kwargs['agency_id'])
        _require_agency_permission(self.request, agency, 'agency.manage_settings')
        serializer.save(agency=agency)


class ManagementAgreementListCreateView(generics.ListCreateAPIView):
    serializer_class = ManagementAgreementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin' or user.is_staff:
            return ManagementAgreement.objects.all().order_by('-created_at')
        from apps.agencies.permissions import agencies_staffed_by
        from django.db.models import Q
        agency_ids = agencies_staffed_by(user).values_list('id', flat=True)
        return ManagementAgreement.objects.filter(
            Q(owner=user) | Q(agency_id__in=agency_ids)
        ).distinct().order_by('-created_at')

    def perform_create(self, serializer):
        property = serializer.validated_data['property']
        agency = serializer.validated_data.get('agency')
        requester = self.request.user
        is_owner = property.landlord_id == requester.id
        is_admin = requester.role == 'admin'
        # An agency can now PROPOSE managing a property it doesn't yet manage, on
        # behalf of a landlord client who isn't the requester - this is the
        # "agency manages properties for other people" path that was missing.
        # It's still safe: the agreement sits in PENDING_SIGNATURES and only
        # becomes ACTIVE once the actual property owner separately signs their
        # side via SignAgreementView(as=owner) - an agency can propose, it can't
        # unilaterally take over a property without the owner's consent.
        is_proposing_agency_staff = agency is not None and has_agency_permission(requester, agency, 'agency.manage_settings')
        if not (is_owner or is_admin or is_proposing_agency_staff):
            raise PermissionDenied(
                "Only the property owner, a platform admin, or a staff member of the proposing agency can create a management agreement."
            )
        serializer.save(owner=property.landlord, status=ManagementAgreement.Status.PENDING_SIGNATURES)


class ManagementAgreementDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = ManagementAgreementSerializer
    queryset = ManagementAgreement.objects.all()
    lookup_field = 'id'


class SignAgreementView(APIView):
    """Owner or agency admin signs an agreement. Once both sides have signed, it becomes ACTIVE."""
    def post(self, request, id):
        agreement = get_object_or_404(ManagementAgreement, id=id)
        as_owner = request.data.get('as', 'owner') == 'owner'

        if as_owner:
            if agreement.owner_id != request.user.id:
                raise PermissionDenied("Only the property owner can sign as owner.")
            agreement.signed_by_owner_at = timezone.now()
        else:
            _require_agency_permission(request, agreement.agency, 'agency.manage_settings')
            agreement.signed_by_agency_at = timezone.now()

        if agreement.signed_by_owner_at and agreement.signed_by_agency_at:
            agreement.status = ManagementAgreement.Status.ACTIVE
            services.assign_property_to_agency(
                property=agreement.property, agency=agreement.agency, start_date=agreement.start_date,
                management_fee_percent=agreement.management_fee_percent, payout_rule=agreement.payout_rule,
                approved_by=request.user, fee_rule=agreement.fee_rule, agreement=agreement,
            )
        agreement.save()
        return success(ManagementAgreementSerializer(agreement).data, message="Agreement signed.")


class PropertyManagementAssignmentListView(generics.ListAPIView):
    """History of who has managed a property, or everything an agency currently manages."""
    serializer_class = PropertyManagementAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        from apps.agencies.permissions import user_can_access_property, agency_membership_for

        qs = PropertyManagementAssignment.objects.select_related('property', 'agency', 'property__landlord')
        property_id = self.request.query_params.get('property')
        agency_id = self.request.query_params.get('agency')
        user = self.request.user

        if user.role == 'admin' or user.is_staff:
            pass  # unrestricted
        elif property_id:
            prop = get_object_or_404(Property, id=property_id)
            if not user_can_access_property(user, prop):
                return PropertyManagementAssignment.objects.none()
        elif agency_id:
            membership = agency_membership_for(user)
            if not membership or str(membership.agency_id) != str(agency_id):
                return PropertyManagementAssignment.objects.none()
        else:
            # No filter given and not an admin: scope to what the caller can see -
            # their own agency's assignments plus assignments on properties they own.
            from django.db.models import Q
            membership = agency_membership_for(user)
            agency_q = Q(agency_id=membership.agency_id) if membership else Q(pk=None)
            return qs.filter(agency_q | Q(property__landlord=user)).order_by('-start_date')

        if property_id:
            qs = qs.filter(property_id=property_id)
        if agency_id:
            qs = qs.filter(agency_id=agency_id)
        return qs.order_by('-start_date')


class AssignPropertyView(APIView):
    """Directly assign a property to an agency (admin/landlord path, bypassing the full agreement flow)."""
    def post(self, request):
        serializer = AssignPropertySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        property = get_object_or_404(Property, id=data['property_id'])
        agency = get_object_or_404(Agency, id=data['agency_id'])

        if not (request.user.role == 'admin' or request.user.is_staff or property.landlord_id == request.user.id):
            raise PermissionDenied("Only the property owner or a platform admin can assign management.")

        fee_rule = None
        if data.get('fee_rule_id'):
            fee_rule = get_object_or_404(AgencyFeeRule, id=data['fee_rule_id'], agency=agency)

        assignment = services.assign_property_to_agency(
            property=property, agency=agency, start_date=data['start_date'],
            management_fee_percent=data.get('management_fee_percent'),
            payout_rule=data.get('payout_rule'), approved_by=request.user, fee_rule=fee_rule,
        )
        return success(
            PropertyManagementAssignmentSerializer(assignment).data,
            message="Property assigned to agency.", status_code=status.HTTP_201_CREATED,
        )


class AssignListingView(APIView):
    """The short-stay/hotel equivalent of AssignPropertyView - a host assigns one of their
    listings (hotel, BnB, serviced apartment, villa) to an agency to manage on their behalf."""
    def post(self, request):
        serializer = AssignListingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        listing = get_object_or_404(Listing, id=data['listing_id'])
        agency = get_object_or_404(Agency, id=data['agency_id'])

        if not (request.user.role == 'admin' or request.user.is_staff or listing.host_id == request.user.id):
            raise PermissionDenied("Only the listing's host or a platform admin can assign management.")

        fee_rule = None
        if data.get('fee_rule_id'):
            fee_rule = get_object_or_404(AgencyFeeRule, id=data['fee_rule_id'], agency=agency)

        assignment = services.assign_listing_to_agency(
            listing=listing, agency=agency, start_date=data['start_date'],
            management_fee_percent=data.get('management_fee_percent'),
            payout_rule=data.get('payout_rule'), approved_by=request.user, fee_rule=fee_rule,
        )
        return success(
            PropertyManagementAssignmentSerializer(assignment).data,
            message="Listing assigned to agency.", status_code=status.HTTP_201_CREATED,
        )


class EndAssignmentView(APIView):
    def post(self, request, id):
        assignment = get_object_or_404(PropertyManagementAssignment, id=id)
        owner_id = assignment.property.landlord_id if assignment.property_id else assignment.listing.host_id
        if not (request.user.role == 'admin' or owner_id == request.user.id
                or has_agency_permission(request.user, assignment.agency, 'agency.manage_assignments')):
            raise PermissionDenied("You cannot end this management assignment.")
        services.end_assignment(assignment, reason=request.data.get('reason', ''), by_user=request.user)
        return success(message="Management assignment ended.")


class OwnerPropertiesView(APIView):
    """A landlord's view of all owned properties, each labelled self-managed or agency-managed.

    Includes the actual management terms (fee %, payout rule, since when, agreement status)
    so the landlord portal can show them without a second round-trip per property.
    """
    def get(self, request):
        properties = Property.objects.filter(landlord=request.user)
        data = []
        for p in properties:
            assignment = PropertyManagementAssignment.active_for_property(p)
            managing_agency = None
            if assignment:
                managing_agency = {
                    'id': str(assignment.agency.id),
                    'name': assignment.agency.name,
                    'email': assignment.agency.email,
                    'phone_number': assignment.agency.phone_number,
                    'assignment_id': str(assignment.id),
                    'management_fee_percent': str(assignment.management_fee_percent),
                    'payout_rule': assignment.payout_rule,
                    'managed_since': assignment.start_date.isoformat(),
                    'agreement_id': str(assignment.agreement.id) if assignment.agreement else None,
                    'agreement_status': assignment.agreement.status if assignment.agreement else None,
                }
            data.append({
                'id': str(p.id), 'name': p.name, 'town': p.town, 'county': p.county,
                'self_managed': assignment is None,
                'managing_agency': managing_agency,
            })
        return success(data)


class OwnerListingsView(APIView):
    """The short-stay/hotel equivalent of OwnerPropertiesView - a host's view of all their
    listings, each labelled self-managed or agency-managed, with the same management terms."""
    def get(self, request):
        listings = Listing.objects.filter(host=request.user)
        data = []
        for l in listings:
            assignment = PropertyManagementAssignment.active_for_listing(l)
            managing_agency = None
            if assignment:
                managing_agency = {
                    'id': str(assignment.agency.id),
                    'name': assignment.agency.name,
                    'email': assignment.agency.email,
                    'phone_number': assignment.agency.phone_number,
                    'assignment_id': str(assignment.id),
                    'management_fee_percent': str(assignment.management_fee_percent),
                    'payout_rule': assignment.payout_rule,
                    'managed_since': assignment.start_date.isoformat(),
                    'agreement_id': str(assignment.agreement.id) if assignment.agreement else None,
                    'agreement_status': assignment.agreement.status if assignment.agreement else None,
                }
            data.append({
                'id': str(l.id), 'name': l.name, 'town': l.town, 'county': l.county,
                'listing_type': l.listing_type,
                'self_managed': assignment is None,
                'managing_agency': managing_agency,
            })
        return success(data)


class OwnerPortfolioView(APIView):
    """
    One call for an owner's whole portfolio: every property and listing they own, who
    manages it (agency or self), who is living/staying there right now, and the revenue
    collected in the chosen period. Works whether or not an agency manages the item -
    the owner always sees their own assets; the agency just shows up as the manager.
    Query params: period_start, period_end (YYYY-MM-DD, default: current month).
    """
    def get(self, request):
        from datetime import date, datetime
        from decimal import Decimal
        from apps.rentals.models import Lease
        from apps.bookings.models import Booking
        from common.calculations import (
            collected_rent_for_period, arrears_for_property,
            collected_booking_revenue_for_period, occupancy_for_period,
        )

        today = date.today()
        try:
            start = datetime.strptime(request.query_params['period_start'], '%Y-%m-%d').date()
            end = datetime.strptime(request.query_params['period_end'], '%Y-%m-%d').date()
        except (KeyError, ValueError):
            start, end = today.replace(day=1), today
        if end < start:
            return error("period_end must be on or after period_start.")

        def manager(assignment):
            if not assignment:
                return None
            a = assignment.agency
            return {
                'id': str(a.id), 'name': a.name, 'email': a.email, 'phone_number': a.phone_number,
                'management_fee_percent': str(assignment.management_fee_percent),
                'payout_rule': assignment.payout_rule, 'managed_since': assignment.start_date.isoformat(),
            }

        properties = []
        for p in Property.objects.filter(landlord=request.user).prefetch_related('units'):
            assignment = PropertyManagementAssignment.active_for_property(p)
            units = list(p.units.all())
            leases = Lease.objects.filter(
                unit__property=p, status=Lease.Status.ACTIVE
            ).select_related('tenant', 'unit')
            collected = collected_rent_for_period(p, start, end)
            fee = Decimal('0')
            if assignment:
                fee = (collected * assignment.management_fee_percent / 100).quantize(Decimal('0.01'))
            properties.append({
                'id': str(p.id), 'name': p.name, 'town': p.town, 'county': p.county,
                'status': p.status, 'self_managed': assignment is None,
                'managed_by': manager(assignment),
                'total_units': len(units),
                'occupied_units': leases.count(),
                'tenants': [{
                    'name': l.tenant.get_full_name() or l.tenant.email,
                    'phone_number': l.tenant.phone_number,
                    'unit': l.unit.unit_number, 'rent_amount': str(l.rent_amount),
                    'lease_end': l.end_date.isoformat() if l.end_date else None,
                } for l in leases],
                'revenue_collected': str(collected),
                'agency_fee': str(fee),
                'net_to_owner': str(collected - fee),
                'arrears': str(arrears_for_property(p, end)),
            })

        listings = []
        for l in Listing.objects.filter(host=request.user):
            assignment = PropertyManagementAssignment.active_for_listing(l)
            collected = collected_booking_revenue_for_period(l, start, end)
            fee = Decimal('0')
            if assignment:
                fee = (collected * assignment.management_fee_percent / 100).quantize(Decimal('0.01'))
            in_house = Booking.objects.filter(
                listing=l, status=Booking.Status.CHECKED_IN
            ).select_related('guest', 'room_type')
            listings.append({
                'id': str(l.id), 'name': l.name, 'town': l.town, 'county': l.county,
                'listing_type': l.listing_type, 'self_managed': assignment is None,
                'managed_by': manager(assignment),
                'occupancy_percent': str(occupancy_for_period(l, start, end)),
                'guests_in_house': [{
                    'name': b.guest.get_full_name() or b.guest.email,
                    'room_type': b.room_type.name if b.room_type_id else '',
                    'check_in': b.check_in_date.isoformat(), 'check_out': b.check_out_date.isoformat(),
                } for b in in_house],
                'revenue_collected': str(collected),
                'agency_fee': str(fee),
                'net_to_owner': str(collected - fee),
            })

        def total(rows, key):
            return str(sum((Decimal(r[key]) for r in rows), Decimal('0')))

        everything = properties + listings
        return success({
            'period_start': start.isoformat(), 'period_end': end.isoformat(),
            'totals': {
                'revenue_collected': total(everything, 'revenue_collected'),
                'agency_fees': total(everything, 'agency_fee'),
                'net_to_owner': total(everything, 'net_to_owner'),
                'agency_managed': sum(1 for r in everything if not r['self_managed']),
                'self_managed': sum(1 for r in everything if r['self_managed']),
            },
            'properties': properties, 'listings': listings,
        })


_RELEASED = (OwnerStatement.Status.ISSUED, OwnerStatement.Status.PAID)


def _owner_visible(user):
    """An owner sees released statements, plus any draft they generated themselves. Drafts
    produced by an agency or by the scheduler are the agency's working copy until issued."""
    return Q(owner=user) & (Q(status__in=_RELEASED) | Q(generated_by=user))


class OwnerStatementListView(generics.ListAPIView):
    serializer_class = OwnerStatementSerializer
    filterset_fields = ['status', 'property', 'listing']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin' or user.is_staff:
            return OwnerStatement.objects.all().order_by('-period_start')
        membership = agency_membership_for(user)
        if membership:
            # Agency staff see their agency's statements; if they also own property
            # themselves they keep seeing their own (released) statements as an owner.
            return OwnerStatement.objects.filter(
                Q(agency=membership.agency) | _owner_visible(user)
            ).order_by('-period_start')
        # Owners only ever see statements that have been issued - a DRAFT is the agency's
        # working copy and is not released to the owner until reviewed and issued.
        # Any non-agency, non-admin user sees only statements where THEY are the owner -
        # `owner` is the authoritative link regardless of whether it's a rental property or
        # a hotel/short-stay listing (and regardless of the user's own role label), so this
        # deliberately isn't restricted to role == 'landlord' - that used to leave hotel
        # owners (and any other non-landlord owner) with an empty list despite genuinely
        # owning statements.
        return OwnerStatement.objects.filter(_owner_visible(user)).order_by('-period_start')


class OwnerStatementDetailView(generics.RetrieveAPIView):
    """
    Retrieve a single owner statement. Deliberately scoped the same way as the list view
    above - a statement contains another party's financial figures (gross rent, commission,
    net payable, a PDF link), so this must never be reachable by UUID alone by an unrelated
    tenant, landlord or agency. Mirrors OwnerStatementListView.get_queryset() on purpose.
    """
    serializer_class = OwnerStatementSerializer
    lookup_field = 'id'

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin' or user.is_staff:
            return OwnerStatement.objects.all()
        membership = agency_membership_for(user)
        if membership:
            return OwnerStatement.objects.filter(Q(agency=membership.agency) | _owner_visible(user))
        return OwnerStatement.objects.filter(_owner_visible(user))


class OwnerStatementAISummaryView(APIView):
    """Plain-English summary of an owner statement's already-computed figures.
    See apps/ai/statement_summary.py for why this doesn't recalculate anything."""

    def post(self, request, id):
        statement = get_object_or_404(OwnerStatement, id=id)
        if statement.agency:
            _require_agency_permission(request, statement.agency, 'statements.view')
        elif not (request.user.role == 'admin' or statement.owner_id == request.user.id):
            raise PermissionDenied("You cannot view this statement.")

        from apps.ai.statement_summary import summarize_statement
        summary = summarize_statement(statement, user=request.user)
        return success({'statement_id': str(statement.id), 'summary': summary})


class GenerateStatementView(APIView):
    def post(self, request):
        serializer = GenerateStatementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        property = get_object_or_404(Property, id=data['property_id'])

        assignment = PropertyManagementAssignment.active_for_property(property)
        if assignment:
            _require_agency_permission(request, assignment.agency, 'statements.issue')
        elif not (request.user.role == 'admin' or property.landlord_id == request.user.id):
            raise PermissionDenied("You cannot generate a statement for this property.")

        statement = services.generate_owner_statement(
            property=property, period_start=data['period_start'], period_end=data['period_end'],
            generated_by=request.user,
        )
        return success(OwnerStatementSerializer(statement).data, message="Statement generated.")


class GenerateListingStatementView(APIView):
    """The short-stay/hotel equivalent of GenerateStatementView, for a Listing rather than a Property."""
    def post(self, request):
        serializer = GenerateListingStatementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        listing = get_object_or_404(Listing, id=data['listing_id'])

        assignment = PropertyManagementAssignment.active_for_listing(listing)
        if assignment:
            _require_agency_permission(request, assignment.agency, 'statements.issue')
        elif not (request.user.role == 'admin' or listing.host_id == request.user.id):
            raise PermissionDenied("You cannot generate a statement for this listing.")

        statement = services.generate_owner_statement_for_listing(
            listing=listing, period_start=data['period_start'], period_end=data['period_end'],
            generated_by=request.user,
        )
        return success(OwnerStatementSerializer(statement).data, message="Statement generated.")


class IssueStatementView(APIView):
    def post(self, request, id):
        statement = get_object_or_404(OwnerStatement, id=id)
        if statement.agency:
            _require_agency_permission(request, statement.agency, 'statements.issue')
        elif not (request.user.role == 'admin' or statement.owner_id == request.user.id):
            raise PermissionDenied("You cannot issue this statement.")
        services.issue_statement(statement, issued_by=request.user)
        return success(OwnerStatementSerializer(statement).data, message="Statement issued to owner.")


class OwnerPayoutListView(generics.ListAPIView):
    serializer_class = OwnerPayoutSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin' or user.is_staff:
            return OwnerPayout.objects.all().order_by('-created_at')
        membership = agency_membership_for(user)
        if membership:
            return OwnerPayout.objects.filter(statement__agency=membership.agency).order_by('-created_at')
        return OwnerPayout.objects.filter(owner=user).order_by('-created_at')


class ExecuteOwnerPayoutView(APIView):
    def post(self, request, statement_id):
        statement = get_object_or_404(OwnerStatement, id=statement_id)
        if statement.status != OwnerStatement.Status.ISSUED:
            return error("Only issued statements can be paid out.")
        if statement.agency:
            _require_agency_permission(request, statement.agency, 'payouts.execute')
        elif not (request.user.role == 'admin' or statement.owner_id == request.user.id):
            raise PermissionDenied("You cannot execute this payout.")

        try:
            payout = services.execute_owner_payout(
                statement, initiated_by=request.user, phone_number=request.data.get('phone_number', ''),
            )
        except ValueError as e:
            return error(str(e))
        return success(OwnerPayoutSerializer(payout).data, message="Payout initiated.", status_code=status.HTTP_201_CREATED)


class AgencyCommissionListView(generics.ListAPIView):
    serializer_class = AgencyCommissionSerializer
    filterset_fields = ['agency', 'property']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin' or user.is_staff:
            return AgencyCommission.objects.all().order_by('-period_start')
        membership = agency_membership_for(user)
        if membership:
            return AgencyCommission.objects.filter(agency=membership.agency).order_by('-period_start')
        return AgencyCommission.objects.none()


class AgencyExpenseListCreateView(generics.ListCreateAPIView):
    serializer_class = AgencyExpenseSerializer
    filterset_fields = ['property', 'category']

    def get_queryset(self):
        return AgencyExpense.objects.filter(agency_id=self.kwargs['agency_id']).order_by('-incurred_on')

    def perform_create(self, serializer):
        agency = get_object_or_404(Agency, id=self.kwargs['agency_id'])
        _require_agency_permission(self.request, agency, 'finance.manage')
        serializer.save(agency=agency, recorded_by=self.request.user)


class AgencyAuditLogListView(generics.ListAPIView):
    serializer_class = AgencyAuditLogSerializer

    def get_queryset(self):
        agency = get_object_or_404(Agency, id=self.kwargs['agency_id'])
        _require_agency_permission(self.request, agency, 'agency.manage_settings')
        return AgencyAuditLog.objects.filter(agency=agency)


class MyPropertiesView(APIView):
    """Every property the caller has a legitimate relationship to, across ownership, agency staffing and tenancy."""
    def get(self, request):
        properties = properties_visible_to(request.user)
        data = [{'id': str(p.id), 'name': p.name, 'town': p.town, 'county': p.county} for p in properties]
        return success(data)


class AgencyRollupDashboardView(APIView):
    """
    Aggregate view across every property this agency currently manages - the piece
    flagged as missing in the AI/Analytics architecture review: agency staff had no
    equivalent of the landlord/admin dashboards, because every existing dashboard
    authorized against the flat User.role field instead of AgencyMembership/AgencyRole.

    Scoping:
      - Platform admin: sees every property this agency manages.
      - Agency Admin / Finance Officer (agency-wide permissions): same - all
        properties under an active PropertyManagementAssignment for this agency.
      - Property Manager / Caretaker / Leasing Agent: scoped down to only the
        properties they have a PropertyStaffAssignment for.
    """
    def get(self, request, agency_id):
        agency = get_object_or_404(Agency, id=agency_id)
        user = request.user

        is_platform_admin = user.role == 'admin' or user.is_staff
        membership = None if is_platform_admin else agency_membership_for(user, agency)
        if not is_platform_admin and not membership:
            raise PermissionDenied("You are not an active member of this agency.")

        managed_properties = Property.objects.filter(
            management_assignments__agency=agency,
            management_assignments__status=PropertyManagementAssignment.Status.ACTIVE,
        ).distinct()

        agency_wide = is_platform_admin or (
            membership and membership.role.role_type in (
                AgencyRole.RoleType.AGENCY_ADMIN, AgencyRole.RoleType.FINANCE_OFFICER,
            )
        )
        if not agency_wide:
            staffed_property_ids = PropertyStaffAssignment.objects.filter(
                membership=membership, is_active=True,
            ).values_list('property_id', flat=True)
            managed_properties = managed_properties.filter(id__in=staffed_property_ids)

        from apps.properties.models import Unit
        from apps.rentals.models import Lease, MaintenanceRequest
        from common.calculations import collected_rent_for_period, arrears_for_property, vacancy_loss_for_period, monthly_totals
        from apps.payments.models import Payment

        today = timezone.now().date()
        month_start = today.replace(day=1)

        units = Unit.objects.filter(property__in=managed_properties)
        occupied = units.filter(status=Unit.Status.OCCUPIED)
        vacant = units.filter(status=Unit.Status.VACANT)

        gross_collected = Decimal('0')
        arrears_total = Decimal('0')
        vacancy_loss_total = Decimal('0')
        per_property = []
        for prop in managed_properties:
            collected = collected_rent_for_period(prop, month_start, today)
            arrears = arrears_for_property(prop, today)
            vacancy_loss = vacancy_loss_for_period(prop, month_start, today)
            gross_collected += collected
            arrears_total += arrears
            vacancy_loss_total += vacancy_loss
            prop_units = units.filter(property=prop)
            per_property.append({
                'property_id': str(prop.id),
                'property_name': prop.name,
                'total_units': prop_units.count(),
                'occupied_units': prop_units.filter(status=Unit.Status.OCCUPIED).count(),
                'vacant_units': prop_units.filter(status=Unit.Status.VACANT).count(),
                'collected_this_month': str(collected),
                'arrears': str(arrears),
                'vacancy_loss_this_month': str(vacancy_loss),
                'open_maintenance_requests': MaintenanceRequest.objects.filter(
                    unit__property=prop, status__in=[MaintenanceRequest.Status.OPEN, MaintenanceRequest.Status.ASSIGNED, MaintenanceRequest.Status.IN_PROGRESS],
                ).count(),
            })

        return success({
            'agency_id': str(agency.id),
            'agency_name': agency.name,
            'scope': 'agency_wide' if agency_wide else 'assigned_properties_only',
            'period': {'start': str(month_start), 'end': str(today)},
            'summary': {
                'total_properties': managed_properties.count(),
                'total_units': units.count(),
                'occupied_units': occupied.count(),
                'vacant_units': vacant.count(),
                'occupancy_rate': round(occupied.count() / units.count() * 100, 1) if units.count() else 0,
                'active_leases': Lease.objects.filter(unit__property__in=managed_properties, status=Lease.Status.ACTIVE).count(),
                'gross_rent_collected_this_month': str(gross_collected),
                'total_arrears': str(arrears_total),
                'estimated_vacancy_loss_this_month': str(vacancy_loss_total),
                'open_maintenance_requests': MaintenanceRequest.objects.filter(
                    unit__property__in=managed_properties,
                    status__in=[MaintenanceRequest.Status.OPEN, MaintenanceRequest.Status.ASSIGNED, MaintenanceRequest.Status.IN_PROGRESS],
                ).count(),
            },
            'properties': per_property,
            # Real month-by-month rent collected across the properties in scope (oldest first).
            'collected_by_month': monthly_totals(
                Payment.objects.filter(
                    status=Payment.Status.COMPLETED, invoice__invoice_type='rent',
                    invoice__lease__unit__property__in=managed_properties,
                ), 'completed_at',
            ),
        })
