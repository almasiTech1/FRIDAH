import hashlib
import hmac
import logging
import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .bot_commands import get_tenant_by_phone, balance_summary_text, lease_summary_text, log_maintenance_request

logger = logging.getLogger('apps.notifications')

HELP_TEXT = (
    "FRIDAH WhatsApp Assistant\n\n"
    "Send one of:\n"
    "BALANCE - check your outstanding rent balance\n"
    "LEASE - see your current lease details\n"
    "MAINTENANCE <description> - log a maintenance request\n"
    "HELP - show this message"
)


def send_whatsapp_message(to_phone, body):
    """Send a plain-text reply via the WhatsApp Cloud API. No-op with a log line if not configured."""
    if not settings.WHATSAPP_ACCESS_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        logger.info("[WHATSAPP:DEV] To %s: %s", to_phone, body)
        return True
    url = f"https://graph.facebook.com/v20.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": body},
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        logger.error("WhatsApp send failed to %s: %s", to_phone, e)
        return False


def handle_command(tenant, raw_text):
    """Returns the reply text for a given incoming message body."""
    text = (raw_text or "").strip()
    command, _, rest = text.partition(' ')
    command = command.upper()

    if not tenant:
        return (
            "We couldn't find a FRIDAH account for this number. "
            "Please register in the app first, or contact your landlord."
        )

    if command == 'BALANCE':
        return balance_summary_text(tenant)
    if command == 'LEASE':
        return lease_summary_text(tenant)
    if command == 'MAINTENANCE':
        _, message = log_maintenance_request(tenant, rest.strip())
        return message
    return HELP_TEXT


class WhatsAppWebhookView(APIView):
    """
    Meta requires a GET verification handshake on setup, then sends incoming messages
    as POSTs to this same URL. The POST body carries no other authentication, so it
    must be verified via the X-Hub-Signature-256 header (HMAC-SHA256 of the raw body
    keyed with the app secret) per Meta's webhook security requirements - without
    this, anyone could POST a fake payload claiming to be from any phone number and
    have the bot read that tenant's balance/lease or log requests as them.
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []  # Meta webhook, verified by signature below rather than rate limit.

    def get(self, request):
        if (
            request.query_params.get('hub.mode') == 'subscribe'
            and request.query_params.get('hub.verify_token') == settings.WHATSAPP_VERIFY_TOKEN
        ):
            return Response(int(request.query_params.get('hub.challenge', 0)))
        return Response(status=403)

    def _signature_valid(self, request):
        app_secret = getattr(settings, 'WHATSAPP_APP_SECRET', '')
        if not app_secret:
            # Dev/staging without a configured app secret: log loudly rather than
            # silently accept unverified payloads, but don't hard-block local testing.
            logger.warning("WHATSAPP_APP_SECRET not configured - webhook signature not verified.")
            return settings.DEBUG

        header_sig = request.META.get('HTTP_X_HUB_SIGNATURE_256', '')
        if not header_sig.startswith('sha256='):
            return False
        expected = hmac.new(app_secret.encode(), request.body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(header_sig[len('sha256='):], expected)

    def post(self, request):
        if not self._signature_valid(request):
            logger.warning("Rejected WhatsApp webhook POST with invalid/missing signature.")
            return Response(status=403)

        try:
            entry = request.data['entry'][0]
            change = entry['changes'][0]['value']
            messages = change.get('messages', [])
        except (KeyError, IndexError):
            return Response({"status": "ignored"})  # status callbacks etc, not a message

        for msg in messages:
            from_phone = msg.get('from', '')
            text = msg.get('text', {}).get('body', '')
            tenant = get_tenant_by_phone(from_phone)
            reply = handle_command(tenant, text)
            send_whatsapp_message(from_phone, reply)

        return Response({"status": "received"})
