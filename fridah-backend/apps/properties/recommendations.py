"""
Smart Property Recommendations - from the FRIDAH 2.0 market-trends/product plan:
"Use saved properties, searches, views, budget, bedrooms, amenities and location
preferences to produce personalized recommendations and match scores."

Deliberately rule-based rather than routed through the Claude-backed AI features
(property_assistant.py etc.) - the plan's own Technical Architecture section
recommends exactly this: "Create a recommendation service separate from the AI
language model so ranking is measurable and can operate even when an LLM is
unavailable." A fixed, inspectable scoring function also means "why was this
recommended" has a real, debuggable answer (each match's `reasons` list), not
a model-generated post-hoc explanation.

v1 scope: county/town/property_type/rent-range matching against the user's own
saved-property and rental-application history. Not built (documented, not
silently skipped): view/click tracking, amenity-level matching, and a real
"searches" signal - none of those are captured anywhere in the platform today,
so this only uses signals that actually exist.
"""
from decimal import Decimal

from django.db.models import Min, Q


def _preference_profile(user):
    """Build a lightweight preference profile from what this user has actually
    saved or applied for. Applications are weighted higher than saves (a saved
    property is passive interest; an application is an active commitment)."""
    from apps.properties.models import SavedProperty
    from apps.rentals.models import RentalApplication

    counties, towns, types, rents = {}, {}, {}, []

    for sp in SavedProperty.objects.filter(user=user).select_related('property'):
        p = sp.property
        counties[p.county] = counties.get(p.county, 0) + 1
        towns[p.town] = towns.get(p.town, 0) + 1
        types[p.property_type] = types.get(p.property_type, 0) + 1

    for app in RentalApplication.objects.filter(tenant=user).select_related('unit__property'):
        p = app.unit.property
        counties[p.county] = counties.get(p.county, 0) + 2
        towns[p.town] = towns.get(p.town, 0) + 2
        types[p.property_type] = types.get(p.property_type, 0) + 2
        rents.append(app.unit.rent_amount)

    return {
        'counties': counties, 'towns': towns, 'types': types,
        'rent_range': (min(rents) * Decimal('0.8'), max(rents) * Decimal('1.2')) if rents else None,
        'has_history': bool(counties or towns or types),
    }


def get_recommendations(user, limit=10):
    """Returns (recommendations, is_personalized). is_personalized is False for
    the cold-start fallback (recent listings, optionally scoped to the user's
    profile county/town) so the client can label the list honestly rather than
    implying a match score that doesn't really exist yet."""
    from apps.properties.models import Property

    profile = _preference_profile(user)

    already_seen_ids = set(
        Property.objects.filter(saved_by__user=user).values_list('id', flat=True)
    ) | set(
        Property.objects.filter(units__rental_applications__tenant=user).values_list('id', flat=True)
    )

    candidates = (
        Property.objects.filter(status=Property.Status.ACTIVE)
        .exclude(id__in=already_seen_ids)
        .annotate(min_rent=Min('units__rent_amount'))
    )

    if not profile['has_history']:
        fallback = candidates
        if getattr(user, 'county', None):
            fallback = fallback.filter(county=user.county) or fallback
        results = list(fallback.order_by('-created_at')[:limit])
        return (
            [{'property': p, 'score': None, 'reasons': ['Recently listed']} for p in results],
            False,
        )

    scored = []
    # Capped candidate pool: a full-table Python scoring pass doesn't need to
    # scale further than this for a v1 rule-based pass - see module docstring.
    for p in candidates.order_by('-created_at')[:300]:
        score = 0
        reasons = []
        if profile['towns'].get(p.town):
            score += 3
            reasons.append(f'In {p.town}, an area you\'ve shown interest in')
        elif profile['counties'].get(p.county):
            score += 2
            reasons.append(f'In {p.county}, matching your search area')
        if profile['types'].get(p.property_type):
            score += 2
            reasons.append(f'{p.get_property_type_display()} - a type you\'ve looked at before')
        if profile['rent_range'] and p.min_rent is not None:
            lo, hi = profile['rent_range']
            if lo <= p.min_rent <= hi:
                score += 2
                reasons.append('Within your typical budget range')
        if score > 0:
            scored.append({'property': p, 'score': score, 'reasons': reasons})

    scored.sort(key=lambda r: r['score'], reverse=True)
    return scored[:limit], True
