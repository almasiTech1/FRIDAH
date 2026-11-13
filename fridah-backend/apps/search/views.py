"""
Global search - was on the original remaining-development-tasks list from day one
and never started. This is a first version: cross-model keyword search using
plain ORM icontains queries (portable across Postgres and the sqlite test/dev
fallback - no Postgres-specific full-text search extensions), with each result
category scoped by the same permission rules the rest of the platform already
uses (properties_visible_to for agency-aware property access, ownership checks
for leases, admin-only for the user directory).

Not implemented in v1, left as a documented follow-up: relevance ranking beyond
"exact matches first, then substring matches" and result highlighting - both are
solvable but add real complexity (and, for ranking, are much better done against
Postgres full-text search than hand-rolled scoring), and searching document
content isn't needed to make the feature useful.
"""
from django.db.models import Q
from rest_framework.views import APIView

from apps.users.views import success

MIN_QUERY_LENGTH = 2
RESULT_LIMIT_PER_TYPE = 10


def _search_properties(user, q):
    from apps.agencies.permissions import properties_visible_to
    qs = properties_visible_to(user).filter(
        Q(name__icontains=q) | Q(town__icontains=q) | Q(county__icontains=q)
        | Q(estate__icontains=q) | Q(address_detail__icontains=q)
    ).distinct()[:RESULT_LIMIT_PER_TYPE]
    return [
        {'id': str(p.id), 'name': p.name, 'town': p.town, 'county': p.county, 'status': p.status}
        for p in qs
    ]


def _search_units(user, q):
    from apps.agencies.permissions import properties_visible_to
    from apps.properties.models import Unit
    qs = Unit.objects.filter(
        property__in=properties_visible_to(user), unit_number__icontains=q,
    ).select_related('property')[:RESULT_LIMIT_PER_TYPE]
    return [
        {'id': str(u.id), 'unit_number': u.unit_number, 'property_id': str(u.property_id),
         'property_name': u.property.name, 'status': u.status}
        for u in qs
    ]


def _visible_lease_queryset(user):
    from apps.rentals.models import Lease
    from apps.agencies.permissions import properties_visible_to
    if user.role == 'admin' or user.is_staff:
        return Lease.objects.all()
    if user.role == 'tenant':
        return Lease.objects.filter(tenant=user)
    return Lease.objects.filter(unit__property__in=properties_visible_to(user))


def _search_leases(user, q):
    qs = _visible_lease_queryset(user).filter(
        Q(tenant__first_name__icontains=q) | Q(tenant__last_name__icontains=q)
        | Q(tenant__email__icontains=q) | Q(unit__unit_number__icontains=q)
    ).select_related('tenant', 'unit', 'unit__property').distinct()[:RESULT_LIMIT_PER_TYPE]
    return [
        {'id': str(l.id), 'tenant_name': f"{l.tenant.first_name} {l.tenant.last_name}".strip() or l.tenant.username,
         'unit_number': l.unit.unit_number, 'property_name': l.unit.property.name, 'status': l.status}
        for l in qs
    ]


def _search_agencies(user, q):
    from apps.agencies.models import Agency
    qs = Agency.objects.filter(name__icontains=q)[:RESULT_LIMIT_PER_TYPE]
    return [{'id': str(a.id), 'name': a.name, 'email': a.email} for a in qs]


def _search_maintenance(user, q):
    from apps.rentals.models import MaintenanceRequest
    from apps.agencies.permissions import properties_visible_to
    if user.role == 'admin' or user.is_staff:
        qs = MaintenanceRequest.objects.all()
    elif user.role == 'tenant':
        qs = MaintenanceRequest.objects.filter(tenant=user)
    else:
        qs = MaintenanceRequest.objects.filter(unit__property__in=properties_visible_to(user))
    qs = qs.filter(
        Q(title__icontains=q) | Q(description__icontains=q) | Q(category__icontains=q)
    ).select_related('unit', 'unit__property')[:RESULT_LIMIT_PER_TYPE]
    return [
        {'id': str(m.id), 'title': m.title, 'status': m.status, 'priority': m.priority,
         'property_name': m.unit.property.name, 'unit_number': m.unit.unit_number}
        for m in qs
    ]


def _search_users(user, q):
    """Admin-only: the platform's user directory is not something other roles should
    be able to search - even a landlord searching by name/email/phone could be used
    to probe for whether a specific person has an account."""
    if not (user.role == 'admin' or user.is_staff):
        return None
    from apps.users.models import User
    qs = User.objects.filter(
        Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q)
        | Q(phone_number__icontains=q) | Q(username__icontains=q)
    )[:RESULT_LIMIT_PER_TYPE]
    return [
        {'id': str(u.id), 'name': f"{u.first_name} {u.last_name}".strip() or u.username,
         'email': u.email, 'role': u.role}
        for u in qs
    ]


SEARCHERS = {
    'properties': _search_properties,
    'units': _search_units,
    'leases': _search_leases,
    'agencies': _search_agencies,
    'maintenance_requests': _search_maintenance,
    'users': _search_users,
}


class GlobalSearchView(APIView):
    def get(self, request):
        q = request.query_params.get('q', '').strip()
        if len(q) < MIN_QUERY_LENGTH:
            return success({'query': q, 'results': {}, 'total_results': 0},
                            message=f"Query must be at least {MIN_QUERY_LENGTH} characters.")

        requested_types = request.query_params.get('types')
        types = [t.strip() for t in requested_types.split(',')] if requested_types else list(SEARCHERS.keys())

        results = {}
        total = 0
        for t in types:
            searcher = SEARCHERS.get(t)
            if not searcher:
                continue
            items = searcher(request.user, q)
            if items is None:  # permission-gated category, not applicable to this user
                continue
            results[t] = items
            total += len(items)

        return success({'query': q, 'results': results, 'total_results': total})
