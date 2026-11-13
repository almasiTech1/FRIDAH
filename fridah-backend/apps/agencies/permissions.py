"""
Relationship-based authorization.

Per the FRIDAH spec, "being a participant in a conversation alone is not sufficient" -
access must be justified by an actual relationship: ownership, an active management
assignment, a lease, a maintenance/service-job assignment, or a platform-admin role.
This module centralizes those checks so every app (properties, rentals, payments,
chat, services) can share one authorization surface instead of re-deriving it.
"""
from rest_framework.permissions import BasePermission
from .models import AgencyMembership, PropertyManagementAssignment, PropertyStaffAssignment


def agency_membership_for(user, agency=None):
    """Active membership for a user, optionally scoped to one agency."""
    if not user.is_authenticated:
        return None
    qs = AgencyMembership.objects.filter(user=user, status=AgencyMembership.Status.ACTIVE)
    if agency is not None:
        qs = qs.filter(agency=agency)
    return qs.select_related('role', 'agency').first()


def agencies_staffed_by(user):
    """All agencies where this user has an active membership."""
    from .models import Agency
    return Agency.objects.filter(
        memberships__user=user, memberships__status=AgencyMembership.Status.ACTIVE
    ).distinct()


def has_agency_permission(user, agency, code):
    membership = agency_membership_for(user, agency)
    return bool(membership and membership.has_permission(code))


def managing_agency_for_property(property):
    """The agency currently managing a property, or None if self-managed."""
    assignment = PropertyManagementAssignment.active_for_property(property)
    return assignment.agency if assignment else None


def user_can_access_property(user, property, required_permission=None):
    """
    True if `user` has a legitimate relationship to `property`:
      - platform admin
      - the owning landlord
      - agency staff assigned to the property (assignment-level, or agency-admin/finance
        with an agency-wide permission), while the agency's management assignment is active
      - a tenant with an active lease on a unit in the property (view-level only)
    """
    if not user.is_authenticated:
        return False
    if user.role == 'admin' or user.is_staff:
        return True
    if property.landlord_id == user.id:
        return True

    assignment = PropertyManagementAssignment.active_for_property(property)
    if assignment:
        membership = agency_membership_for(user, assignment.agency)
        if membership:
            is_staff_assigned = PropertyStaffAssignment.objects.filter(
                property=property, membership=membership, is_active=True
            ).exists()
            if is_staff_assigned:
                return required_permission is None or membership.has_permission(required_permission)
            # Agency-wide roles (agency admin / finance officer) can act on any property
            # under an active assignment without a per-property staff row, provided they
            # hold the relevant permission.
            if required_permission is None:
                return membership.role.role_type in (
                    membership.role.RoleType.AGENCY_ADMIN, membership.role.RoleType.FINANCE_OFFICER,
                )
            return membership.has_permission(required_permission)

    if required_permission is None:
        from apps.rentals.models import Lease
        return Lease.objects.filter(
            tenant=user, unit__property=property, status=Lease.Status.ACTIVE
        ).exists()
    return False


def properties_visible_to(user):
    """
    Queryset of Property rows the user has a legitimate relationship to.

    Mirrors user_can_access_property()'s semantics rather than the older, coarser
    "any property under any agency you're staffed at" rule: agency-wide roles
    (Agency Admin, Finance Officer) see every property their agency manages, but
    Property Manager / Caretaker / Leasing Agent are scoped down to only the
    properties they hold an active PropertyStaffAssignment for - which is the
    entire documented purpose of that model ("restricts a specific agency staff
    member's operational access to specific properties"). The two functions had
    drifted apart; this was caught while building the global search feature,
    which is why every existing caller (MyPropertiesView, MaintenanceAnalyticsView,
    the properties list view, and search itself) gets the more correct scoping
    automatically rather than each needing its own fix.
    """
    from apps.properties.models import Property
    from apps.rentals.models import Lease
    from .models import AgencyRole
    from django.db.models import Q

    if not user.is_authenticated:
        return Property.objects.none()
    if user.role == 'admin' or user.is_staff:
        return Property.objects.all()

    tenant_property_ids = Lease.objects.filter(
        tenant=user, status=Lease.Status.ACTIVE
    ).values_list('unit__property_id', flat=True)

    agency_wide_agency_ids = AgencyMembership.objects.filter(
        user=user, status=AgencyMembership.Status.ACTIVE,
        role__role_type__in=[AgencyRole.RoleType.AGENCY_ADMIN, AgencyRole.RoleType.FINANCE_OFFICER],
    ).values_list('agency_id', flat=True)

    staffed_property_ids = PropertyStaffAssignment.objects.filter(
        membership__user=user, membership__status=AgencyMembership.Status.ACTIVE, is_active=True,
    ).values_list('property_id', flat=True)

    return Property.objects.filter(
        Q(landlord=user)
        | Q(submitted_by=user)
        | Q(management_assignments__agency_id__in=agency_wide_agency_ids, management_assignments__status='active')
        | Q(id__in=staffed_property_ids)
        | Q(id__in=tenant_property_ids)
    ).distinct()


class HasAgencyPermission(BasePermission):
    """DRF permission requiring the caller to hold `required_permission` in the resolved agency."""
    required_permission = None

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.role == 'admin' or request.user.is_staff:
            return True
        agency_id = view.kwargs.get('agency_id') or request.data.get('agency')
        if not agency_id:
            return True  # object-level check applies instead
        from .models import Agency
        try:
            agency = Agency.objects.get(id=agency_id)
        except Agency.DoesNotExist:
            return False
        return has_agency_permission(request.user, agency, self.required_permission)


class IsAgencyMember(BasePermission):
    """Caller must be an active member of at least one agency."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and agency_membership_for(request.user) is not None
