import hashlib
import hmac
import json

import pytest
from django.test import override_settings

WHATSAPP_URL = '/api/v1/whatsapp/webhook/'
USSD_URL = '/api/v1/ussd/webhook/'


@pytest.mark.django_db
class TestWhatsAppWebhookSignature:
    """Regression tests for the fixed WhatsApp webhook spoofing vulnerability:
    previously any client could POST a fabricated 'messages' payload with an
    arbitrary phone number and have the bot act as that tenant, with no proof
    the request actually came from Meta."""

    @override_settings(WHATSAPP_APP_SECRET='test-app-secret', DEBUG=False)
    def test_post_without_signature_header_rejected(self, api_client):
        body = {'entry': [{'changes': [{'value': {'messages': []}}]}]}
        resp = api_client.post(WHATSAPP_URL, data=json.dumps(body), content_type='application/json')
        assert resp.status_code == 403

    @override_settings(WHATSAPP_APP_SECRET='test-app-secret', DEBUG=False)
    def test_post_with_wrong_signature_rejected(self, api_client):
        body = {'entry': [{'changes': [{'value': {'messages': []}}]}]}
        resp = api_client.post(
            WHATSAPP_URL, data=json.dumps(body), content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256='sha256=' + '0' * 64,
        )
        assert resp.status_code == 403

    @override_settings(WHATSAPP_APP_SECRET='test-app-secret', DEBUG=False)
    def test_post_with_valid_signature_accepted(self, api_client):
        body_bytes = json.dumps({'entry': [{'changes': [{'value': {'messages': []}}]}]}).encode()
        sig = hmac.new(b'test-app-secret', body_bytes, hashlib.sha256).hexdigest()
        resp = api_client.post(
            WHATSAPP_URL, data=body_bytes, content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256=f'sha256={sig}',
        )
        assert resp.status_code == 200

    @override_settings(WHATSAPP_APP_SECRET='test-app-secret', DEBUG=False)
    def test_signature_for_one_payload_does_not_validate_another(self, api_client):
        """A signature computed over one payload must not validate a different,
        attacker-modified payload (proves body-bytes, not just header presence, are checked)."""
        original = json.dumps({'entry': [{'changes': [{'value': {'messages': []}}]}]}).encode()
        sig = hmac.new(b'test-app-secret', original, hashlib.sha256).hexdigest()
        tampered = json.dumps({'entry': [{'changes': [{'value': {'messages': [{'from': 'attacker'}]}}]}]}).encode()
        resp = api_client.post(
            WHATSAPP_URL, data=tampered, content_type='application/json',
            HTTP_X_HUB_SIGNATURE_256=f'sha256={sig}',
        )
        assert resp.status_code == 403


@pytest.mark.django_db
class TestUssdWebhookSharedSecret:
    """Regression tests for the fixed USSD webhook spoofing vulnerability: Africa's
    Talking doesn't sign requests, so phoneNumber in the POST body was otherwise an
    unverified claim - anyone who found the URL could read/act as any tenant."""

    @override_settings(USSD_SHARED_SECRET='test-ussd-secret')
    def test_post_without_secret_rejected(self, api_client, tenant):
        resp = api_client.post(USSD_URL, {'sessionId': 'abc', 'phoneNumber': tenant.phone_number, 'text': ''})
        assert resp.status_code == 403

    @override_settings(USSD_SHARED_SECRET='test-ussd-secret')
    def test_post_with_wrong_secret_rejected(self, api_client, tenant):
        resp = api_client.post(
            USSD_URL + '?secret=wrong-secret',
            {'sessionId': 'abc', 'phoneNumber': tenant.phone_number, 'text': ''},
        )
        assert resp.status_code == 403

    @override_settings(USSD_SHARED_SECRET='test-ussd-secret')
    def test_post_with_correct_secret_accepted(self, api_client, tenant):
        resp = api_client.post(
            USSD_URL + '?secret=test-ussd-secret',
            {'sessionId': 'abc', 'phoneNumber': tenant.phone_number, 'text': ''},
        )
        assert resp.status_code == 200
        assert resp.content.decode().startswith('CON')
