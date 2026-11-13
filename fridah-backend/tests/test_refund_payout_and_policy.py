"""Automatic refund payouts (M-Pesa B2C), B2C callback safety, callback URL routing, and the editable refund policy."""
import inspect
from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import resolve

from apps.audit.models import AuditLog
from apps.notifications.models import Notification
from apps.payments import refunds
from apps.payments.models import MpesaTransaction, Payment, Payout, Refund, WalletTransaction
from apps.payments.mpesa_client import MpesaClient, MpesaError
from apps.payments.services import debit_wallet, get_wallet_balance, mark_payment_completed
from apps.rentals.models import Invoice

SAFARICOM = '196.201.214.200'
B2C = '/api/v1/payments/mpesa/b2c-result/'


@pytest.fixture
def admin(admin_user):
    admin_user.role = 'admin'
    admin_user.save()
    return admin_user


@pytest.fixture
def paid(lease, tenant, landlord):
    invoice = Invoice.objects.create(lease=lease, tenant=tenant, invoice_type='rent', amount=Decimal('20000'),
                                     period_start=date(2026, 3, 1), period_end=date(2026, 3, 31), due_date=date(2026, 3, 5))
    p = Payment.objects.create(payer=tenant, invoice=invoice, amount=Decimal('20000'), method='mpesa_stk',
                               status='pending', phone_number='+254712345678')
    MpesaTransaction.objects.create(payment=p, checkout_request_id='ws_CO_5', phone_number='+254712345678',
                                    amount=Decimal('20000'), mpesa_receipt_number='QHX1ABC555')
    mark_payment_completed(p, mpesa_receipt='QHX1ABC555', received_amount='20000')
    p.refresh_from_db()
    return p


@pytest.fixture
def approved(paid, tenant, admin):
    r = refunds.request_refund(paid, tenant, Decimal('3000'), 'Charged twice')
    return refunds.approve_refund(r, admin)


@pytest.fixture
def prod_like(settings):
    settings.DEBUG = False
    settings.MPESA_ALLOWED_IPS = [SAFARICOM]
    settings.TRUSTED_PROXY_COUNT = 1
    return settings


@pytest.fixture
def b2c_ok(monkeypatch, settings):
    settings.MPESA_B2C_REFUNDS_ENABLED = True
    calls = []

    def fake(self, phone_number, amount, remarks, occasion='Payout', **kw):
        calls.append({'phone': phone_number, 'amount': amount, 'remarks': remarks, 'occasion': occasion})
        return {'ConversationID': f'AG_{len(calls)}', 'ResponseCode': '0'}

    monkeypatch.setattr(MpesaClient, 'b2c_payment', fake)
    return calls


def result_body(conv, code=0, receipt='QHX9B2C001', desc='The service request is processed successfully.'):
    params = {'ResultParameters': {'ResultParameter': [{'Key': 'TransactionReceipt', 'Value': receipt}]}} if code == 0 else {}
    return {'Result': {'ResultCode': code, 'ResultDesc': desc, 'ConversationID': conv, **params}}


# ===================================================================== callback routing
class TestCallbackUrls:
    def test_every_callback_path_the_client_sends_is_a_real_route(self):
        for fn in (MpesaClient.stk_push, MpesaClient.b2c_payment, MpesaClient.register_c2b_urls):
            for name, p in inspect.signature(fn).parameters.items():
                if name.endswith('_path'):
                    assert p.default.startswith('/api/v1/'), f'{fn.__name__}.{name} = {p.default}'
                    assert resolve(p.default).route, f'{p.default} does not resolve'


# ===================================================================== refund payout
@pytest.mark.django_db
class TestRefundPayout:
    def test_disabled_by_default(self, approved, admin):
        with pytest.raises(ValidationError, match='not enabled'):
            refunds.initiate_refund_payout(approved, admin)

    def test_sends_whole_shillings_to_the_payers_phone_once(self, approved, admin, b2c_ok):
        payout = refunds.initiate_refund_payout(approved, admin)
        assert payout.status == Payout.Status.PROCESSING and payout.conversation_id == 'AG_1'
        assert payout.refund_id == approved.id and payout.recipient_id == approved.payment.payer_id
        assert b2c_ok[0]['amount'] == Decimal('3000.00') and b2c_ok[0]['phone'] == '+254712345678'
        assert 'refund' in b2c_ok[0]['remarks'].lower()
        with pytest.raises(ValidationError, match='already in progress'):
            refunds.initiate_refund_payout(approved, admin)          # no double click / double payment
        assert len(b2c_ok) == 1

    def test_validation(self, approved, paid, tenant, admin, b2c_ok):
        with pytest.raises(PermissionDenied):
            refunds.initiate_refund_payout(approved, tenant)
        pending = refunds.request_refund(paid, tenant, Decimal('1000'), 'More')
        with pytest.raises(ValidationError, match='approved'):
            refunds.initiate_refund_payout(pending, admin)
        odd = refunds.approve_refund(refunds.request_refund(paid, tenant, Decimal('1000.50'), 'Partial'), admin)
        with pytest.raises(ValidationError, match='whole shillings'):
            refunds.initiate_refund_payout(odd, admin)
        assert b2c_ok == []                                          # nothing was sent for any of them

    def test_mpesa_rejection_is_recorded_and_can_be_retried(self, approved, admin, settings, monkeypatch):
        settings.MPESA_B2C_REFUNDS_ENABLED = True
        monkeypatch.setattr(MpesaClient, 'b2c_payment', lambda self, *a, **k: (_ for _ in ()).throw(MpesaError('Insufficient float')))
        with pytest.raises(ValidationError, match='Insufficient float'):
            refunds.initiate_refund_payout(approved, admin)
        assert Payout.objects.get(refund=approved).status == Payout.Status.FAILED
        monkeypatch.setattr(MpesaClient, 'b2c_payment', lambda self, *a, **k: {'ConversationID': 'AG_RETRY'})
        assert refunds.initiate_refund_payout(approved, admin).status == Payout.Status.PROCESSING

    def test_success_callback_marks_the_refund_paid_with_the_receipt_exactly_once(self, api_client, approved, admin, b2c_ok, prod_like, tenant):
        payout = refunds.initiate_refund_payout(approved, admin)
        for _ in range(3):                                           # Safaricom retries callbacks
            r = api_client.post(B2C, result_body(payout.conversation_id), format='json', HTTP_X_FORWARDED_FOR=SAFARICOM)
            assert r.status_code == 200
        approved.refresh_from_db(); payout.refresh_from_db()
        assert approved.status == Refund.Status.PAID_OUT and approved.payout_reference == 'QHX9B2C001'
        assert payout.status == Payout.Status.COMPLETED
        assert Notification.objects.filter(user=tenant, title='Refund paid').count() == 1
        # a late failure notice cannot undo a completed payout
        api_client.post(B2C, result_body(payout.conversation_id, code=2001, desc='x'), format='json', HTTP_X_FORWARDED_FOR=SAFARICOM)
        payout.refresh_from_db(); approved.refresh_from_db()
        assert payout.status == Payout.Status.COMPLETED and approved.status == Refund.Status.PAID_OUT

    def test_failure_callback_keeps_the_refund_approved_credits_no_wallet_and_alerts_admins(
            self, api_client, approved, admin, b2c_ok, prod_like, landlord):
        wallet_before = get_wallet_balance(landlord)
        entries_before = WalletTransaction.objects.count()
        payout = refunds.initiate_refund_payout(approved, admin)
        for _ in range(2):
            api_client.post(B2C, result_body(payout.conversation_id, code=2001, desc='The initiator information is invalid'),
                            format='json', HTTP_X_FORWARDED_FOR=SAFARICOM)
        approved.refresh_from_db(); payout.refresh_from_db()
        assert payout.status == Payout.Status.FAILED and approved.status == Refund.Status.APPROVED
        assert WalletTransaction.objects.count() == entries_before and get_wallet_balance(landlord) == wallet_before
        assert Notification.objects.filter(user=admin, title='Refund payout failed').count() == 1
        assert refunds.initiate_refund_payout(approved, admin).status == Payout.Status.PROCESSING   # retry allowed

    def test_spoofed_callback_cannot_mark_a_refund_paid(self, api_client, approved, admin, b2c_ok, prod_like):
        payout = refunds.initiate_refund_payout(approved, admin)
        r = api_client.post(B2C, result_body(payout.conversation_id), format='json', HTTP_X_FORWARDED_FOR=f'{SAFARICOM}, 203.0.113.9')
        assert r.status_code == 403
        approved.refresh_from_db()
        assert approved.status == Refund.Status.APPROVED

    def test_api_exposes_availability_and_the_action(self, api_client, approved, admin, b2c_ok):
        api_client.force_authenticate(user=admin)
        data = api_client.get('/api/v1/refunds/').data['results'][0]
        assert data['auto_payout_available'] is True and data['payout_status'] is None
        r = api_client.post(f'/api/v1/refunds/{approved.id}/pay-out/')
        assert r.status_code == 200 and r.data['data']['payout_status'] == 'processing'
        again = api_client.post(f'/api/v1/refunds/{approved.id}/pay-out/')
        assert again.status_code == 400 and 'already in progress' in again.data['error']['message']


@pytest.mark.django_db
class TestWalletPayoutFailureIsIdempotent:
    """Regression: a repeated B2C failure callback used to credit the landlord's wallet every time."""

    def test_credited_back_exactly_once(self, api_client, landlord, prod_like):
        from apps.payments.services import credit_wallet
        credit_wallet(landlord, Decimal('10000'), 'seed')
        payout = Payout.objects.create(recipient=landlord, amount=Decimal('4000'), phone_number='+254712345678',
                                       status=Payout.Status.PROCESSING, conversation_id='AG_W1')
        debit_wallet(landlord, Decimal('4000'), 'Payout', related_payout=payout)
        assert get_wallet_balance(landlord) == Decimal('6000.00')
        for _ in range(3):
            api_client.post(B2C, result_body('AG_W1', code=2001, desc='failed'), format='json', HTTP_X_FORWARDED_FOR=SAFARICOM)
        assert get_wallet_balance(landlord) == Decimal('10000.00')
        assert WalletTransaction.objects.filter(related_payout=payout, entry_type='credit').count() == 1

    def test_a_failure_for_a_payout_that_never_debited_the_wallet_credits_nothing(self, api_client, landlord, prod_like):
        Payout.objects.create(recipient=landlord, amount=Decimal('500'), phone_number='+254712345678',
                              status=Payout.Status.PROCESSING, conversation_id='AG_W2')
        api_client.post(B2C, result_body('AG_W2', code=2001, desc='failed'), format='json', HTTP_X_FORWARDED_FOR=SAFARICOM)
        assert get_wallet_balance(landlord) == 0


# ===================================================================== editable policy
@pytest.mark.django_db
class TestRefundPolicy:
    URL = '/api/v1/refunds/policy/'

    def test_defaults_visible_to_everyone_editable_by_admins_only(self, api_client, admin, tenant):
        api_client.force_authenticate(user=tenant)
        d = api_client.get(self.URL).data['data']
        assert Decimal(str(d['admin_approval_above'])) == Decimal('5000.00') and d['window_days'] == 180
        assert d['self_approval_allowed'] is False and d['auto_payout_enabled'] is False
        assert api_client.put(self.URL, {'admin_approval_above': 1, 'window_days': 1}, format='json').status_code == 403
        api_client.force_authenticate(user=admin)
        r = api_client.put(self.URL, {'admin_approval_above': '1000', 'window_days': 90}, format='json')
        assert r.status_code == 200 and r.data['data']['window_days'] == 90
        api_client.force_authenticate(user=tenant)
        assert Decimal(str(api_client.get(self.URL).data['data']['admin_approval_above'])) == Decimal('1000.00')

    def test_validation(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        for body in ({'admin_approval_above': -1, 'window_days': 30}, {'admin_approval_above': 5000000, 'window_days': 30},
                     {'admin_approval_above': 100, 'window_days': 0}, {'admin_approval_above': 100, 'window_days': 9999},
                     {'admin_approval_above': 'abc', 'window_days': 30}, {}):
            assert api_client.put(self.URL, body, format='json').status_code == 400, body

    def test_changing_the_limit_changes_who_must_approve_new_requests(self, paid, tenant, landlord, admin, api_client):
        assert refunds.request_refund(paid, tenant, Decimal('3000'), 'a').approval_level == Refund.ApprovalLevel.RECIPIENT
        api_client.force_authenticate(user=admin)
        api_client.put(self.URL, {'admin_approval_above': 2000, 'window_days': 180}, format='json')
        assert refunds.request_refund(paid, tenant, Decimal('3000'), 'b').approval_level == Refund.ApprovalLevel.ADMIN

    def test_window_change_is_enforced_and_every_change_is_audited(self, paid, tenant, admin, api_client):
        from datetime import timedelta
        from django.utils import timezone
        Payment.objects.filter(pk=paid.pk).update(completed_at=timezone.now() - timedelta(days=60))
        paid.refresh_from_db()
        refunds.request_refund(paid, tenant, Decimal('100'), 'ok')
        api_client.force_authenticate(user=admin)
        api_client.put(self.URL, {'admin_approval_above': 5000, 'window_days': 30}, format='json')
        with pytest.raises(ValidationError, match='within 30 days'):
            refunds.request_refund(paid, tenant, Decimal('100'), 'late')
        log = AuditLog.objects.filter(action='refund.policy_changed').latest('created_at')
        assert log.changes['before']['window_days'] == '180' and log.changes['after']['window_days'] == '30'
