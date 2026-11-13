from unittest.mock import patch
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from apps.factories import UserFactory, LeaseFactory
from apps.rentals.models import Invoice
from apps.payments.models import Payment
from apps.payments.mpesa_client import MpesaClient


class MpesaClientUnitTests(APITestCase):
    def test_normalize_phone_variants(self):
        self.assertEqual(MpesaClient._normalize_phone("+254712345678"), "254712345678")
        self.assertEqual(MpesaClient._normalize_phone("0712345678"), "254712345678")
        self.assertEqual(MpesaClient._normalize_phone("254712345678"), "254712345678")


class STKPushTests(APITestCase):
    def setUp(self):
        self.lease = LeaseFactory()
        self.invoice = Invoice.objects.create(
            lease=self.lease, tenant=self.lease.tenant, amount=25000,
            period_start="2026-01-01", period_end="2026-01-31", due_date="2026-01-05",
        )
        self.client.force_authenticate(self.lease.tenant)

    @patch.object(MpesaClient, 'stk_push')
    def test_stk_push_initiate_creates_payment(self, mock_stk):
        mock_stk.return_value = {
            'payload': {}, 'response': {'CheckoutRequestID': 'ws_CO_123', 'MerchantRequestID': 'mr_123'}
        }
        payload = {
            "phone_number": "+254712345678", "amount": "25000",
            "invoice_id": str(self.invoice.id), "description": "Rent payment",
        }
        response = self.client.post(reverse('stk_push'), payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Payment.objects.filter(invoice=self.invoice).exists())
        payment = Payment.objects.get(invoice=self.invoice)
        self.assertEqual(payment.status, Payment.Status.PROCESSING)

    @patch.object(MpesaClient, 'stk_push')
    def test_stk_push_failure_marks_payment_failed(self, mock_stk):
        from apps.payments.mpesa_client import MpesaError
        mock_stk.side_effect = MpesaError("Network error")
        payload = {"phone_number": "+254712345678", "amount": "25000", "invoice_id": str(self.invoice.id)}
        response = self.client.post(reverse('stk_push'), payload)
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        payment = Payment.objects.get(invoice=self.invoice)
        self.assertEqual(payment.status, Payment.Status.FAILED)


class MpesaCallbackTests(APITestCase):
    def setUp(self):
        self.lease = LeaseFactory()
        self.invoice = Invoice.objects.create(
            lease=self.lease, tenant=self.lease.tenant, amount=25000,
            period_start="2026-01-01", period_end="2026-01-31", due_date="2026-01-05",
        )
        self.payment = Payment.objects.create(
            payer=self.lease.tenant, invoice=self.invoice, amount=25000,
            phone_number="+254712345678", status=Payment.Status.PROCESSING,
        )
        from apps.payments.models import MpesaTransaction
        self.mpesa_txn = MpesaTransaction.objects.create(
            payment=self.payment, checkout_request_id="ws_CO_999",
            phone_number="+254712345678", amount=25000,
        )

    @patch('apps.payments.views.is_valid_safaricom_ip', return_value=True)
    def test_successful_callback_marks_payment_completed(self, mock_ip_check):
        # is_valid_safaricom_ip() is real-IP-allowlist gated (and correctly does NOT
        # auto-pass under DEBUG=False, which is what pytest-django forces for every
        # test regardless of the environment's DEBUG setting) — mocking it here so
        # this test exercises the callback-processing logic, not the IP allowlist
        # itself (that's covered by its own dedicated test below).
        body = {
            "Body": {
                "stkCallback": {
                    "CheckoutRequestID": "ws_CO_999",
                    "ResultCode": 0,
                    "ResultDesc": "Success",
                    "CallbackMetadata": {"Item": [
                        {"Name": "MpesaReceiptNumber", "Value": "QGH7XYZ123"},
                        {"Name": "TransactionDate", "Value": 20260101120000},
                    ]}
                }
            }
        }
        response = self.client.post(reverse('mpesa_stk_callback'), body, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.COMPLETED)

    def test_callback_from_untrusted_ip_rejected(self):
        """Regression coverage for the M-Pesa callback IP allowlist itself (separate
        from the mocked-IP test above, which exercises the callback processing logic)."""
        body = {
            "Body": {"stkCallback": {
                "CheckoutRequestID": "ws_CO_999", "ResultCode": 0, "ResultDesc": "Success",
                "CallbackMetadata": {"Item": [
                    {"Name": "MpesaReceiptNumber", "Value": "QGH7XYZ123"},
                    {"Name": "TransactionDate", "Value": 20260101120000},
                ]},
            }},
        }
        response = self.client.post(
            reverse('mpesa_stk_callback'), body, format='json', REMOTE_ADDR='1.2.3.4',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PROCESSING)  # untouched

    def test_callback_from_allowlisted_safaricom_ip_accepted(self):
        body = {
            "Body": {"stkCallback": {
                "CheckoutRequestID": "ws_CO_999", "ResultCode": 0, "ResultDesc": "Success",
                "CallbackMetadata": {"Item": [
                    {"Name": "MpesaReceiptNumber", "Value": "QGH7XYZ123"},
                    {"Name": "TransactionDate", "Value": 20260101120000},
                ]},
            }},
        }
        response = self.client.post(
            reverse('mpesa_stk_callback'), body, format='json', REMOTE_ADDR='196.201.214.200',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.COMPLETED)
