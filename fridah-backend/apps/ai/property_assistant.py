import logging
from django.db.models import Q, Min

from .client import call_claude, extract_json, AIUnavailableError

logger = logging.getLogger('apps.ai')

PARSE_SYSTEM_PROMPT = """You extract structured search filters from a free-text property search query for a \
Kenyan rental platform. Respond with ONLY a JSON object, no other text, no markdown fences.

Schema:
{
  "county": string or null,
  "town": string or null,
  "min_bedrooms": integer or null,
  "max_bedrooms": integer or null,
  "min_rent": integer or null,
  "max_rent": integer or null,
  "property_type": one of ["apartment","bungalow","maisonette","townhouse","commercial","hostel","bedsitter","single_room"] or null,
  "keywords": array of strings (amenities, landmarks, or descriptive terms mentioned, e.g. "near Kenyatta University", "parking", "furnished")
}

Only fill fields the query actually implies. Kenyan Shillings amounts like "30k" or "30,000" mean 30000. \
"Near X" or a named place goes in keywords, not county/town, unless X is itself a known town/county."""


def parse_search_query(query_text: str) -> dict:
    """Turns a free-text query into structured filters. Raises AIUnavailableError if AI isn't configured."""
    from django.conf import settings

    text = call_claude(
        feature='property_assistant',
        model=settings.AI_MODEL_FAST,
        system=PARSE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": query_text}],
        max_tokens=300,
    )
    try:
        parsed = extract_json(text)
    except ValueError:
        logger.warning("Property assistant: failed to parse filters from '%s'", query_text)
        parsed = {}
    return parsed


def search_properties(filters: dict, limit: int = 12):
    """Runs the parsed filters against real listed properties. Same underlying model as the public search."""
    from apps.properties.models import Property

    qs = Property.objects.filter(status=Property.Status.ACTIVE)

    if filters.get('county'):
        qs = qs.filter(county__icontains=filters['county'])
    if filters.get('town'):
        qs = qs.filter(town__icontains=filters['town'])
    if filters.get('property_type'):
        qs = qs.filter(property_type=filters['property_type'])

    unit_q = Q()
    if filters.get('min_bedrooms'):
        unit_q &= Q(units__bedrooms__gte=filters['min_bedrooms'])
    if filters.get('max_bedrooms'):
        unit_q &= Q(units__bedrooms__lte=filters['max_bedrooms'])
    if filters.get('min_rent'):
        unit_q &= Q(units__rent_amount__gte=filters['min_rent'])
    if filters.get('max_rent'):
        unit_q &= Q(units__rent_amount__lte=filters['max_rent'])
    if unit_q:
        qs = qs.filter(unit_q)

    # Keywords are free-text (amenities/landmarks) - the DB can't reason about proximity to
    # "Kenyatta University", so we do a broad OR match across name/description/amenities/estate
    # as a first-pass filter, then let the AI explanation step do the real judgment call on
    # whether each result actually fits the keyword intent.
    for kw in filters.get('keywords') or []:
        if _is_meaningful_keyword(kw):
            qs = qs.filter(
                Q(name__icontains=kw) | Q(description__icontains=kw) | Q(estate__icontains=kw)
                | Q(amenities__icontains=kw)
            )

    qs = qs.annotate(min_rent_amount=Min('units__rent_amount')).distinct().order_by('-created_at')
    return list(qs[:limit])


def _is_meaningful_keyword(kw: str) -> bool:
    return isinstance(kw, str) and len(kw.strip()) >= 3


EXPLAIN_SYSTEM_PROMPT = """You write a single short sentence (max 20 words) explaining why each property \
result matches a user's search query, for a Kenyan rental platform. Respond with ONLY a JSON array of strings, \
one per property, in the same order given, no other text. Be specific and honest - if a property is only a \
partial match, say so briefly rather than overselling it."""


def explain_matches(query_text: str, properties) -> list:
    """One batched call to explain why each of the (already DB-filtered) results matches the original query."""
    from django.conf import settings

    if not properties:
        return []

    summaries = []
    for p in properties:
        summaries.append(
            f"{p.name} - {p.property_type} in {p.estate or ''} {p.town}, {p.county}. "
            f"{p.vacant_units_count} vacant units. "
            f"Rent from KES {p.min_rent_amount or 'N/A'}. Amenities: {', '.join(p.amenities or [])}."
        )

    prompt = f"Original search: \"{query_text}\"\n\nProperties:\n" + "\n".join(
        f"{i + 1}. {s}" for i, s in enumerate(summaries)
    )

    try:
        text = call_claude(
            feature='property_assistant',
            model=settings.AI_MODEL_QUALITY,
            system=EXPLAIN_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
        )
        explanations = extract_json(text)
        if isinstance(explanations, list) and len(explanations) == len(properties):
            return explanations
    except (AIUnavailableError, ValueError, Exception) as e:
        logger.warning("Property assistant: explanation generation failed: %s", e)

    # Fallback: a plain, honest, non-AI description rather than nothing.
    return [f"Matches your search criteria in {p.town}, {p.county}." for p in properties]


def run_assistant_search(query_text: str, user=None):
    """Full pipeline: parse -> search -> explain. Used by the API view."""
    filters = parse_search_query(query_text)
    properties = search_properties(filters)
    explanations = explain_matches(query_text, properties)
    return {
        'parsed_filters': filters,
        'results': [
            {'property_id': str(p.id), 'explanation': explanation}
            for p, explanation in zip(properties, explanations)
        ],
    }
