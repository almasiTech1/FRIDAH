import base64
import logging

from .client import call_claude, extract_json

logger = logging.getLogger('apps.ai')

TRIAGE_SYSTEM_PROMPT = """You triage a maintenance issue from a tenant's photo for a Kenyan rental platform. \
Identify the likely problem category and how urgent it is. Be conservative - if the photo is unclear or \
ambiguous, say so rather than guessing confidently.

Respond with ONLY a JSON object, no other text:
{
  "category": one of ["plumbing", "electrical", "structural", "appliance", "pest_control", "locks_security", "hvac", "other"],
  "priority": one of ["low", "medium", "high", "urgent"] (urgent = active water/electrical/fire/safety hazard),
  "description": string (1-2 sentences describing what you see and why it needs attention),
  "confidence": one of ["low", "moderate", "high"],
  "safety_concern": boolean (true if this could be a safety/health hazard, e.g. exposed wiring, gas smell risk, structural damage)
}"""


def triage_photo(*, image_bytes: bytes, media_type: str, tenant_description: str = '', user=None) -> dict:
    from django.conf import settings

    content = [
        {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": base64.b64encode(image_bytes).decode()},
        },
        {
            "type": "text",
            "text": f"Tenant's description (if any): {tenant_description or 'none provided'}\n\nTriage this issue.",
        },
    ]

    text = call_claude(
        feature='maintenance_triage',
        model=settings.AI_MODEL_FAST,
        system=TRIAGE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
        max_tokens=300,
        user=user,
    )
    return extract_json(text)


def suggest_provider_category(triage_category: str):
    """Maps the AI's triage category to a real ServiceCategory on the platform, if one exists."""
    from apps.services.models import ServiceCategory

    category_keywords = {
        'plumbing': ['plumb'],
        'electrical': ['electric'],
        'structural': ['carpen', 'structur', 'construct'],
        'appliance': ['appliance', 'repair'],
        'pest_control': ['pest'],
        'locks_security': ['lock', 'security'],
        'hvac': ['hvac', 'air condition', 'ac '],
    }
    keywords = category_keywords.get(triage_category, [])
    for kw in keywords:
        match = ServiceCategory.objects.filter(name__icontains=kw).first()
        if match:
            return match
    return None
