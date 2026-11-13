import json
import logging
import time

from django.conf import settings

logger = logging.getLogger('apps.ai')


class AIUnavailableError(Exception):
    """Raised when ANTHROPIC_API_KEY isn't configured, so callers can degrade gracefully."""


def is_ai_configured() -> bool:
    return bool(settings.ANTHROPIC_API_KEY)


def _get_client():
    if not is_ai_configured():
        raise AIUnavailableError("ANTHROPIC_API_KEY is not configured.")
    import anthropic
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def call_claude(
    *, feature, model, system, messages, max_tokens=1024, user=None, request_id=None,
):
    """
    Thin wrapper around messages.create() that logs every call to AIInteractionLog and
    normalizes errors. `messages` follows the standard Anthropic content-block format,
    so callers can pass text-only or text+image content directly.

    Returns the raw text of the model's reply (first text block).
    Raises AIUnavailableError if not configured, or re-raises API errors after logging.
    """
    from .models import AIInteractionLog

    if not is_ai_configured():
        raise AIUnavailableError("AI features are not configured on this server.")

    client = _get_client()
    start = time.monotonic()
    log_kwargs = dict(user=user, feature=feature, model=model)

    try:
        response = client.messages.create(
            model=model, system=system, messages=messages, max_tokens=max_tokens,
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        text = "".join(block.text for block in response.content if getattr(block, 'type', None) == 'text')

        AIInteractionLog.objects.create(
            **log_kwargs,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            succeeded=True,
            latency_ms=latency_ms,
        )
        return text

    except Exception as e:
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.error("Claude API call failed (feature=%s): %s", feature, e)
        AIInteractionLog.objects.create(
            **log_kwargs, succeeded=False, error_message=str(e)[:2000], latency_ms=latency_ms,
        )
        raise


def extract_json(text: str):
    """
    Models occasionally wrap JSON in prose or markdown fences despite instructions.
    Pulls out the first {...} or [...] block and parses it, raising ValueError with
    the original text attached if nothing parseable is found.
    """
    text = text.strip()
    if text.startswith('```'):
        text = text.strip('`')
        if text.startswith('json'):
            text = text[4:]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    for open_char, close_char in (('{', '}'), ('[', ']')):
        start = text.find(open_char)
        end = text.rfind(close_char)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                continue

    raise ValueError(f"Could not parse JSON from model response: {text[:500]}")
