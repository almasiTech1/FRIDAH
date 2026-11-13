"""Payment confirmation hardening (report 3.8): spoofing, duplicates, amount checks, state safety."""
from datetime import date
from decimal import Decimal

import pytest
from django.test import RequestFactory

from apps.payments.models import MpesaTransaction, Payment, PaymentAllocation, WalletTransaction
from apps.payments.security import get_client_ip, is_valid_safaricom_ip
from apps.payments.services import get_wallet_balance, mark_payment_completed, mark_payment_failed
from apps.rentals.models import Invoice

SAFARICOM = '196.201.214.200'
CALLBACK = '/api/v1/payments/mpesa/stk-callback/'


@pytest.fixture
def invoice(lease, tenant):
    return Invoice.objects.create(
        lease=lease, tenant=tenant, invoice_type='rent', amount=Decimal('20000'),
        period_start=date(2026, 3, 1), period_end=date(2026, 3, 31), due_date=date(2026, 3, 5),
    )


@pytest.fixture
def pending(invoice, tenant):
    p = Payment.objects.create(payer=tenant, invoice=invoice, amount=Decimal('20000'), method='mpesa_stk',
                               status='pending', phone_number='+254712345678')
    MpesaTransaction.objects.create(payment=p, checkout_request_id='ws_CO_1', phone_number='+254712345678',
                                    amount=Decimal('20000'))
    return p


def stk_body(amount=20000, code=0, receipt='QHX1ABC123'):
    items = [{'Name': 'Amount', 'Value': amount}, {'Name': 'MpesaReceiptNumber', 'Value': receipt},
             {'Name': 'TransactionDate', 'Value': 20260310101010}]
    return {'Body': {'stkCallback': {'CheckoutRequestID': 'ws_CO_1', 'ResultCode': code, 'ResultDesc': 'ok',
                                     'CallbackMetadata': {'Item': items} if code == 0 else {}}}}


@pytest.fixture
def prod_like(settings):
    settings.DEBUG = False
    settings.MPESA_ALLOWED_IPS = [SAFARICOM]
    settings.TRUSTED_PROXY_COUNT = 1
    return settings


@pytest.mark.usefixtures('prod_like')
class TestCallerIdentity:
    def req(self, xff=None, remote='10.0.0.5'):
        meta = {'REMOTE_ADDR': remote}
        if xff:
            meta['HTTP_X_FORWARDED_FOR'] = xff
        return RequestFactory().post('/x/', **meta)

    def test_client_supplied_forwarded_for_cannot_impersonate_safaricom(self):
        # attacker prepends Safaricom's IP; our proxy appends the attacker's real address
        r = self.req(xff=f'{SAFARICOM}, 203.0.113.9')
        assert get_client_ip(r) == '203.0.113.9'
        assert is_valid_safaricom_ip(r) is False

    def test_genuine_safaricom_through_our_proxy_is_accepted(self):
        assert is_valid_safaricom_ip(self.req(xff=SAFARICOM)) is True

    def test_no_proxy_ignores_the_header(self, prod_like):
        prod_like.TRUSTED_PROXY_COUNT = 0
        r = self.req(xff=SAFARICOM, remote='203.0.113.9')
        assert get_client_ip(r) == '203.0.113.9' and is_valid_safaricom_ip(r) is False


@pytest.mark.django_db
@pytest.mark.usefixtures('prod_like')
class TestCallbackEndpoint:
    def test_spoofed_callback_is_rejected_and_nothing_changes(self, api_client, pending, invoice):
        r = api_client.post(CALLBACK, stk_body(), format='json',
                            HTTP_X_FORWARDED_FOR=f'{SAFARICOM}, 203.0.113.9')
        assert r.status_code == 403
        pending.refresh_from_db(); invoice.refresh_from_db()
        assert pending.status == 'pending' and invoice.amount_paid == 0

    def test_genuine_callback_completes_once_even_if_delivered_twice(self, api_client, pending, invoice, landlord):
        for _ in range(3):   # Safaricom retries
            r = api_client.post(CALLBACK, stk_body(), format='json', HTTP_X_FORWARDED_FOR=SAFARICOM)
            assert r.status_code == 200
        pending.refresh_from_db(); invoice.refresh_from_db()
        assert pending.status == 'completed' and invoice.status == 'paid'
        assert invoice.amount_paid == Decimal('20000')
        assert PaymentAllocation.objects.filter(payment=pending).count() == 1
        assert WalletTransaction.objects.filter(related_payment=pending).count() == 1
        credited = get_wallet_balance(landlord)
        assert Decimal('0') < credited < Decimal('20000')  # net of platform commission, once

    def test_c2b_validation_requires_safaricom_ip(self, api_client):
        url = '/api/v1/payments/mpesa/c2b/validation/'
        from django.urls import reverse, NoReverseMatch
        try:
            url = reverse('mpesa_c2b_validation')
        except NoReverseMatch:
            pass
        assert api_client.post(url, {}, format='json', HTTP_X_FORWARDED_FOR=f'{SAFARICOM}, 203.0.113.9').status_code == 403


@pytest.mark.django_db
class TestPaymentStateSafety:
    def test_poller_and_callback_racing_cannot_double_apply(self, pending, invoice):
        mark_payment_completed(pending, mpesa_receipt='QHX1ABC123', received_amount='20000')
        mark_payment_completed(pending)                         # the polling fallback arrives second
        invoice.refresh_from_db()
        assert invoice.amount_paid == Decimal('20000')
        assert PaymentAllocation.objects.filter(payment=pending).count() == 1

    def test_amount_mismatch_is_disputed_and_applies_nothing(self, pending, invoice, landlord):
        mark_payment_completed(pending, mpesa_receipt='QHX1ABC123', received_amount='200')
        pending.refresh_from_db(); invoice.refresh_from_db()
        assert pending.status == Payment.Status.DISPUTED and 'mismatch' in pending.failure_reason.lower()
        assert invoice.amount_paid == 0 and get_wallet_balance(landlord) == 0
        from apps.audit.models import AuditLog
        assert AuditLog.objects.filter(action='payment.amount_mismatch').exists()
        # a later "success" retry must not resurrect a disputed payment
        mark_payment_completed(pending, received_amount='20000')
        invoice.refresh_from_db()
        assert invoice.amount_paid == 0

    def test_late_failure_notice_cannot_undo_a_completed_payment(self, pending):
        mark_payment_completed(pending, received_amount='20000')
        mark_payment_failed(pending, 'Request cancelled by user')
        pending.refresh_from_db()
        assert pending.status == Payment.Status.COMPLETED and not pending.failure_reason

    def test_failure_still_works_for_a_pending_payment(self, pending):
        mark_payment_failed(pending, 'Insufficient funds')
        pending.refresh_from_db()
        assert pending.status == 'failed' and pending.failure_reason == 'Insufficient funds'

    def test_money_taken_after_in_app_cancel_is_still_recorded(self, pending, invoice):
        pending.status = Payment.Status.CANCELLED
        pending.save()
        mark_payment_completed(pending, received_amount='20000')   # M-Pesa debited the customer anyway
        invoice.refresh_from_db()
        assert invoice.status == 'paid'


@pytest.mark.django_db
class TestDisputeResolution:
    @pytest.fixture
    def disputed(self, pending):
        mark_payment_completed(pending, received_amount='200')
        pending.refresh_from_db()
        assert pending.status == Payment.Status.DISPUTED
        return pending

    def _post(self, client, user, payment, **body):
        client.force_authenticate(user=user)
        return client.post(f'/api/v1/payments/{payment.id}/resolve-dispute/', body, format='json')

    def test_admin_confirm_applies_exactly_once(self, api_client, disputed, invoice, admin_user, landlord):
        admin_user.role = 'admin'; admin_user.save()
        r = self._post(api_client, admin_user, disputed, action='confirm', reason='Verified on Safaricom statement')
        assert r.status_code == 200
        invoice.refresh_from_db()
        assert invoice.status == 'paid' and invoice.amount_paid == Decimal('20000')
        assert self._post(api_client, admin_user, disputed, action='confirm', reason='again').status_code == 400
        assert PaymentAllocation.objects.filter(payment=disputed).count() == 1

    def test_admin_void_credits_nothing(self, api_client, disputed, invoice, admin_user, landlord):
        admin_user.role = 'admin'; admin_user.save()
        assert self._post(api_client, admin_user, disputed, action='void', reason='Customer paid KES 200 only').status_code == 200
        disputed.refresh_from_db(); invoice.refresh_from_db()
        assert disputed.status == Payment.Status.REVERSED and invoice.amount_paid == 0
        assert get_wallet_balance(landlord) == 0

    def test_reason_required_and_non_admins_blocked(self, api_client, disputed, admin_user, landlord):
        admin_user.role = 'admin'; admin_user.save()
        assert self._post(api_client, admin_user, disputed, action='void', reason=' ').status_code == 400
        assert self._post(api_client, landlord, disputed, action='confirm', reason='x').status_code == 403
