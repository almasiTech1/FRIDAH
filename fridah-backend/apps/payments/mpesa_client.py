import base64
import logging
from datetime import datetime

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger('apps.payments')

OAUTH_CACHE_KEY = 'mpesa:access_token'


class MpesaError(Exception):
    pass


class MpesaClient:
    """
    Safaricom Daraja 2.0 client.
    Handles OAuth token caching (Redis), STK Push (Lipa na M-Pesa), B2C disbursement,
    and C2B registration.
    """

    def __init__(self):
        self.base_url = settings.MPESA_BASE_URL
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.shortcode = settings.MPESA_SHORTCODE
        self.passkey = settings.MPESA_PASSKEY
        self.callback_base = settings.MPESA_CALLBACK_BASE_URL

    # ------------------------------------------------------------------
    # OAuth
    # ------------------------------------------------------------------
    def get_access_token(self):
        cached = cache.get(OAUTH_CACHE_KEY)
        if cached:
            return cached

        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        creds = base64.b64encode(f"{self.consumer_key}:{self.consumer_secret}".encode()).decode()
        headers = {"Authorization": f"Basic {creds}"}

        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            token = data['access_token']
            expires_in = int(data.get('expires_in', 3599))
            # Cache for slightly less than the token's actual lifetime
            cache.set(OAUTH_CACHE_KEY, token, timeout=max(expires_in - 60, 60))
            return token
        except requests.RequestException as e:
            logger.error("M-Pesa OAuth failed: %s", e)
            raise MpesaError(f"Failed to authenticate with M-Pesa: {e}")

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.get_access_token()}",
            "Content-Type": "application/json",
        }

    def _password(self, timestamp):
        raw = f"{self.shortcode}{self.passkey}{timestamp}"
        return base64.b64encode(raw.encode()).decode()

    # ------------------------------------------------------------------
    # STK Push (Lipa Na M-Pesa Online)
    # ------------------------------------------------------------------
    def stk_push(self, phone_number, amount, account_reference, transaction_desc, callback_path="/api/v1/payments/mpesa/stk-callback/"):
        """
        phone_number must be in 2547XXXXXXXX format (no +).
        """
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": self._password(timestamp),
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),
            "PartyA": self._normalize_phone(phone_number),
            "PartyB": self.shortcode,
            "PhoneNumber": self._normalize_phone(phone_number),
            "CallBackURL": f"{self.callback_base}{callback_path}",
            "AccountReference": account_reference[:20],
            "TransactionDesc": transaction_desc[:100],
        }
        try:
            resp = requests.post(
                f"{self.base_url}/mpesa/stkpush/v1/processrequest",
                json=payload, headers=self._headers(), timeout=20
            )
            data = resp.json()
            if resp.status_code != 200 or data.get('ResponseCode') not in ('0', 0):
                logger.error("STK push rejected: %s", data)
                raise MpesaError(data.get('errorMessage') or data.get('ResponseDescription', 'STK push failed'))
            return {'payload': payload, 'response': data}
        except requests.RequestException as e:
            logger.error("STK push request failed: %s", e)
            raise MpesaError(f"M-Pesa STK push request failed: {e}")

    def stk_query(self, checkout_request_id):
        """Query the status of an STK push transaction (used by polling task)."""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": self._password(timestamp),
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id,
        }
        try:
            resp = requests.post(
                f"{self.base_url}/mpesa/stkpushquery/v1/query",
                json=payload, headers=self._headers(), timeout=20
            )
            return resp.json()
        except requests.RequestException as e:
            logger.error("STK query failed: %s", e)
            raise MpesaError(f"M-Pesa STK query failed: {e}")

    # ------------------------------------------------------------------
    # B2C (Payouts to landlords / providers / hosts)
    # ------------------------------------------------------------------
    def b2c_payment(self, phone_number, amount, remarks, occasion="Payout", callback_path="/api/v1/payments/mpesa/b2c-result/", timeout_path="/api/v1/payments/mpesa/b2c-timeout/"):
        payload = {
            "InitiatorName": settings.MPESA_INITIATOR_NAME,
            "SecurityCredential": self._security_credential(),
            "CommandID": "BusinessPayment",
            "Amount": int(amount),
            "PartyA": self.shortcode,
            "PartyB": self._normalize_phone(phone_number),
            "Remarks": remarks[:100],
            "QueueTimeOutURL": f"{self.callback_base}{timeout_path}",
            "ResultURL": f"{self.callback_base}{callback_path}",
            "Occasion": occasion[:100],
        }
        try:
            resp = requests.post(
                f"{self.base_url}/mpesa/b2c/v3/paymentrequest",
                json=payload, headers=self._headers(), timeout=20
            )
            data = resp.json()
            if resp.status_code != 200:
                logger.error("B2C payment rejected: %s", data)
                raise MpesaError(data.get('errorMessage', 'B2C payment failed'))
            return data
        except requests.RequestException as e:
            logger.error("B2C request failed: %s", e)
            raise MpesaError(f"M-Pesa B2C request failed: {e}")

    def _security_credential(self):
        """
        Encrypts the initiator password with Safaricom's public certificate (RSA).
        In production, the cert (sandbox or prod) must be bundled under config/certs/.
        """
        from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15
        from cryptography.x509 import load_pem_x509_certificate, load_der_x509_certificate
        import os

        cert_name = 'SandboxCertificate.cer' if settings.MPESA_ENV == 'sandbox' else 'ProductionCertificate.cer'
        cert_path = os.path.join(settings.BASE_DIR, 'config', 'certs', cert_name)
        with open(cert_path, 'rb') as f:
            cert_data = f.read()

        # Safaricom's .cer files are X.509 certificates, not raw public keys, and may be
        # PEM or DER encoded depending on where they were downloaded from. Try PEM first
        # (the documented format) and fall back to DER.
        try:
            certificate = load_pem_x509_certificate(cert_data)
        except ValueError:
            certificate = load_der_x509_certificate(cert_data)
        public_key = certificate.public_key()

        encrypted = public_key.encrypt(settings.MPESA_INITIATOR_PASSWORD.encode(), PKCS1v15())
        return base64.b64encode(encrypted).decode()

    # ------------------------------------------------------------------
    # C2B registration (paybill direct payments, e.g. for hotel/bnb deposits)
    # ------------------------------------------------------------------
    def register_c2b_urls(self, confirmation_path="/api/v1/payments/mpesa/c2b-confirmation/", validation_path="/api/v1/payments/mpesa/c2b-validation/"):
        payload = {
            "ShortCode": self.shortcode,
            "ResponseType": "Completed",
            "ConfirmationURL": f"{self.callback_base}{confirmation_path}",
            "ValidationURL": f"{self.callback_base}{validation_path}",
        }
        resp = requests.post(
            f"{self.base_url}/mpesa/c2b/v1/registerurl",
            json=payload, headers=self._headers(), timeout=20
        )
        return resp.json()

    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_phone(phone_number):
        """Converts +2547XXXXXXXX or 07XXXXXXXX to 2547XXXXXXXX for Daraja."""
        phone_number = phone_number.strip().replace(' ', '')
        if phone_number.startswith('+'):
            return phone_number[1:]
        if phone_number.startswith('0'):
            return '254' + phone_number[1:]
        return phone_number
