import logging
import statistics

from .client import call_claude, extract_json, AIUnavailableError

logger = logging.getLogger('apps.ai')

ESTIMATE_SYSTEM_PROMPT = """You are a Kenyan rental market analyst. You are given real comparable unit data \
from the platform's own database (not your training data) for a specific area and bedroom count, plus the \
landlord's proposed unit details. Using ONLY the comparable data provided, give a reasoned rent recommendation.

Respond with ONLY a JSON object, no other text:
{
  "recommended_rent": integer (KES, should be grounded in the comparable data given, adjusted for amenities/size),
  "rent_range_low": integer,
  "rent_range_high": integer,
  "occupancy_likelihood": one of ["low", "moderate", "high"],
  "demand_notes": string (1-2 sentences, reference the actual comparable count and any amenity/size reasoning),
  "confidence": one of ["low", "moderate", "high"] (low if fewer than 3 comparables were available)
}

If there are zero or very few comparables, say so honestly in demand_notes and lower confidence accordingly - \
do not invent a number with false confidence."""


def get_comparable_units(county: str, town: str, bedrooms: int, exclude_unit_id=None):
    """Real comparable units from the platform's own data - this grounds the estimate, not the LLM's training data."""
    from apps.properties.models import Unit

    qs = Unit.objects.filter(
        property__status='active',
        property__county__iexact=county,
        bedrooms=bedrooms,
    ).select_related('property')

    if town:
        # Prefer same-town comparables, but fall back to county-wide if too few.
        town_qs = qs.filter(property__town__iexact=town)
        if town_qs.count() >= 3:
            qs = town_qs

    if exclude_unit_id:
        qs = qs.exclude(id=exclude_unit_id)

    return list(qs.order_by('-created_at')[:30])


def estimate_rent(*, county: str, town: str, bedrooms: int, amenities: list, size_sqm=None, user=None) -> dict:
    """
    Full pipeline: pull real comparable units -> compute actual statistics -> ask Claude to
    reason about adjustments and occupancy likelihood using those real numbers as grounding.
    """
    comparables = get_comparable_units(county, town, bedrooms)
    rents = [float(u.rent_amount) for u in comparables if u.rent_amount]

    stats = {
        'comparable_count': len(rents),
        'median_rent': round(statistics.median(rents)) if rents else None,
        'min_rent': round(min(rents)) if rents else None,
        'max_rent': round(max(rents)) if rents else None,
    }

    if not rents:
        return {
            'recommended_rent': None,
            'rent_range_low': None,
            'rent_range_high': None,
            'occupancy_likelihood': 'unknown',
            'demand_notes': (
                f"No comparable {bedrooms}-bedroom units found in {town or county} on the platform yet, "
                f"so we can't ground an estimate in real data. Try a nearby town or check back as more "
                f"listings come online."
            ),
            'confidence': 'none',
            'comparable_stats': stats,
        }

    from django.conf import settings

    prompt = (
        f"Area: {town}, {county}\n"
        f"Bedrooms: {bedrooms}\n"
        f"Amenities: {', '.join(amenities) if amenities else 'none specified'}\n"
        + (f"Size: {size_sqm} sqm\n" if size_sqm else "")
        + f"\nReal comparable units on the platform ({len(rents)} found):\n"
        f"Median rent: KES {stats['median_rent']}\n"
        f"Range: KES {stats['min_rent']} - KES {stats['max_rent']}\n"
    )

    try:
        text = call_claude(
            feature='rent_estimator',
            model=settings.AI_MODEL_FAST,
            system=ESTIMATE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            user=user,
        )
        result = extract_json(text)
        result['comparable_stats'] = stats
        return result
    except (AIUnavailableError, ValueError, Exception) as e:
        logger.warning("Rent estimator: AI reasoning failed, falling back to raw stats: %s", e)
        return {
            'recommended_rent': stats['median_rent'],
            'rent_range_low': stats['min_rent'],
            'rent_range_high': stats['max_rent'],
            'occupancy_likelihood': 'moderate' if len(rents) >= 5 else 'low',
            'demand_notes': f"Based on {len(rents)} comparable units in the area (AI commentary unavailable).",
            'confidence': 'moderate' if len(rents) >= 5 else 'low',
            'comparable_stats': stats,
        }
