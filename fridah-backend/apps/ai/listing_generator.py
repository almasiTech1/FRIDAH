import base64
import logging

from .client import call_claude, extract_json

logger = logging.getLogger('apps.ai')

GENERATE_SYSTEM_PROMPT = """You write property listing copy for a Kenyan rental/hospitality platform, based on \
photos and facts a landlord provides. Be accurate to what's actually visible in the photos - never invent \
amenities, room counts, or features you can't see or weren't told about. Write in a warm, professional tone \
that would appeal to Kenyan renters, without being overly salesy or using superlatives you can't justify.

Respond with ONLY a JSON object, no other text:
{
  "title": string (max 60 chars, catchy but accurate),
  "description": string (2-3 short paragraphs, plain text, no markdown),
  "amenities": array of strings (only amenities actually visible in photos or stated in facts),
  "seo_keywords": array of 5-8 strings (search terms a renter might use to find this property)
}"""


def _image_block(image_bytes: bytes, media_type: str) -> dict:
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": base64.b64encode(image_bytes).decode(),
        },
    }


def generate_listing_copy(*, images: list, facts: dict, user=None) -> dict:
    """
    images: list of (bytes, media_type) tuples - already-read file content, capped by the
    caller (view) to a sane number/size before reaching here.
    facts: landlord-provided details (property_type, bedrooms, county, town, rent_amount, etc)
    """
    from django.conf import settings

    fact_lines = "\n".join(f"{k}: {v}" for k, v in facts.items() if v not in (None, '', []))
    content = [{"type": "text", "text": f"Facts provided by the landlord:\n{fact_lines}\n\nPhotos:"}]
    for img_bytes, media_type in images:
        content.append(_image_block(img_bytes, media_type))
    content.append({"type": "text", "text": "Generate the listing copy now."})

    text = call_claude(
        feature='listing_generator',
        model=settings.AI_MODEL_QUALITY,
        system=GENERATE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
        max_tokens=800,
        user=user,
    )
    return extract_json(text)
