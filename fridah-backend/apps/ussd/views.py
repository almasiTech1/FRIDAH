import logging
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.http import HttpResponse

from apps.notifications.bot_commands import (
    get_tenant_by_phone, balance_summary_text, lease_summary_text, log_maintenance_request,
)

logger = logging.getLogger('apps.ussd')

MAIN_MENU = (
    "CON Welcome to FRIDAH\n"
    "1. Check rent balance\n"
    "2. My lease details\n"
    "3. Log a maintenance issue\n"
    "4. How to pay rent"
)

PAY_INSTRUCTIONS = (
    "END To pay rent, go to M-Pesa > Lipa na M-Pesa > Pay Bill.\n"
    f"Business number: {getattr(settings, 'MPESA_SHORTCODE', '')}\n"
    "Account number: your invoice number (shown in the FRIDAH app or your last SMS reminder)."
)


class UssdWebhookView(APIView):
    """
    Africa's Talking posts sessionId, phoneNumber, and a 'text' field that accumulates
    every screen the user has selected so far, separated by '*' (e.g. '3*Leaking tap').
    The response must start with 'CON ' to show another menu screen, or 'END ' to
    terminate the session - this is a plain-text protocol, not JSON.

    Africa's Talking doesn't sign these requests, so `phoneNumber` in the POST body
    is otherwise just an unverified claim - anyone who found this URL could POST any
    phone number and read that tenant's balance/lease or log a request as them. AT's
    own recommended mitigation (they don't offer per-request HMAC signing) is a
    shared secret in the callback URL, checked below against USSD_SHARED_SECRET.
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []  # Africa's Talking webhook, verified by shared secret below.

    def post(self, request):
        configured_secret = getattr(settings, 'USSD_SHARED_SECRET', '')
        if configured_secret:
            if request.query_params.get('secret') != configured_secret:
                logger.warning("Rejected USSD webhook POST with invalid/missing shared secret.")
                return HttpResponse(status=403)
        else:
            logger.warning("USSD_SHARED_SECRET not configured - webhook is unauthenticated.")

        phone_number = request.data.get('phoneNumber', '')
        text = (request.data.get('text', '') or '').strip()
        levels = text.split('*') if text else []

        tenant = get_tenant_by_phone(phone_number)
        if not tenant:
            return self._respond(
                "END We couldn't find a FRIDAH account for this number. "
                "Please register in the FRIDAH app first."
            )

        if not levels or levels == ['']:
            return self._respond(MAIN_MENU)

        choice = levels[0]

        if choice == '1':
            return self._respond(f"END {balance_summary_text(tenant)}")

        if choice == '2':
            return self._respond(f"END {lease_summary_text(tenant)}")

        if choice == '3':
            if len(levels) == 1:
                return self._respond("CON Briefly describe the issue (e.g. 'Leaking tap in kitchen'):")
            description = '*'.join(levels[1:])  # in case their description itself contains '*'
            _, message = log_maintenance_request(tenant, description)
            return self._respond(f"END {message}")

        if choice == '4':
            return self._respond(PAY_INSTRUCTIONS)

        return self._respond("END Invalid choice. Please dial again.")

    @staticmethod
    def _respond(text):
        # Africa's Talking expects text/plain, not the DRF-default JSON envelope.
        return HttpResponse(text, content_type='text/plain')
