"""Refunds, reversals, reconciliation and settlement reporting."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.notifications.models import Notification
from apps.payments import reconciliation as recon
from apps.payments import refunds
from apps.payments.models import (
    MpesaTransaction, PaybillTransaction, Payment, ReconciliationItem, Refund, WalletTransaction,
)
from apps.payments.services import credit_wallet, debit_wallet, get_wallet_balance, mark_payment_completed
from apps.rentals.models import Invoice
from apps.users.models import User

K = ReconciliationItem.Kind


@pytest.fixture
def admin(admin_user):
    admin_user.role = 'admin'
    admin_user.save()
    return admin_user


@pytest.fixture
def admin2(db):
    return User.objects.create_user(username='admin2', email='admin2@test.com', password='StrongPass123!',
                                    role='admin', phone_number='+254700000081', is_staff=True)


@pytest.fixture
def paid(lease, tenant, landlord):
    """A KES 20,000 rent invoice paid in full: landlord credited 19,000 (5% commission)."""
    invoice = Invoice.objects.create(
        lease=lease, tenant=tenant, invoice_type='rent', amount=Decimal('20000'),
        period_start=date(2026, 3, 1), period_end=date(2026, 3, 31), due_date=date(2026, 3, 5),
    )
    p = Payment.objects.create(payer=tenant, invoice=invoice, amount=Decimal('20000'), method='mpesa_stk',
                               status='pending', phone_number='+254712345678')
    MpesaTransaction.objects.create(payment=p, checkout_request_id='ws_CO_9', phone_number='+254712345678',
                                    amount=Decimal('20000'), mpesa_receipt_number='QHX1ABC123')
    mark_payment_completed(p, mpesa_receipt='QHX1ABC123', received_amount='20000')
    p.refresh_from_db()
    assert get_wallet_balance(landlord) == Decimal('19000.00')
    return p


def req(payment, user, amount, reason='Customer overpaid', **kw):
    return refunds.request_refund(payment, user, Decimal(str(amount)), reason, **kw)


# ===================================================================== refunds
@pytest.mark.django_db
class TestRefundPolicy:
    def test_large_refund_needs_an_administrator_and_unwinds_everything(self, paid, tenant, landlord, admin):
        r = req(paid, tenant, 20000)
        assert r.approval_level == Refund.ApprovalLevel.ADMIN and r.status == Refund.Status.REQUESTED
        with pytest.raises(PermissionDenied):
            refunds.approve_refund(r, landlord)                       # recipient cannot approve a large refund
        refunds.approve_refund(r, admin, 'Verified with customer')
        r.refresh_from_db(); paid.refresh_from_db()
        invoice = paid.invoice; invoice.refresh_from_db()
        assert r.status == Refund.Status.APPROVED and r.recipient_debit == Decimal('19000.00')
        assert invoice.amount_paid == 0 and invoice.status == Invoice.Status.OVERDUE   # due date has passed
        assert paid.allocations.get().amount == 0
        assert paid.status == Payment.Status.REFUNDED and paid.refunded_amount == Decimal('20000')
        assert get_wallet_balance(landlord) == 0
        assert AuditLog.objects.filter(action='refund.approved').exists()
        assert Notification.objects.filter(user=tenant, title__icontains='refund approved').exists()

    def test_small_refund_can_be_approved_by_the_recipient_and_is_proportional(self, paid, tenant, landlord):
        r = req(paid, tenant, 3000)
        assert r.approval_level == Refund.ApprovalLevel.RECIPIENT
        refunds.approve_refund(r, landlord)
        paid.refresh_from_db(); invoice = paid.invoice; invoice.refresh_from_db()
        assert paid.status == Payment.Status.COMPLETED and paid.refunded_amount == Decimal('3000')
        assert invoice.amount_paid == Decimal('17000') and invoice.status == Invoice.Status.PARTIALLY_PAID
        assert get_wallet_balance(landlord) == Decimal('16150.00')   # 19,000 less 3,000/20,000 of it = 2,850

    def test_nobody_approves_their_own_request(self, paid, landlord, admin, admin2):
        r = req(paid, admin, 20000)
        with pytest.raises(PermissionDenied):
            refunds.approve_refund(r, admin)
        refunds.approve_refund(r, admin2)                                # a different administrator can
        assert Refund.objects.get(pk=r.pk).status == Refund.Status.APPROVED

    def test_recipient_requesting_must_be_approved_by_someone_else(self, paid, landlord, admin):
        r = req(paid, landlord, 1000, 'Tenant paid twice')
        with pytest.raises(PermissionDenied):
            refunds.approve_refund(r, landlord)
        refunds.approve_refund(r, admin)

    def test_cannot_refund_more_than_was_paid_even_with_open_requests(self, paid, tenant):
        req(paid, tenant, 12000)
        with pytest.raises(ValidationError, match='8000'):
            req(paid, tenant, 8001)
        req(paid, tenant, 8000)                                         # exactly the remainder is fine

    def test_over_refund_blocked_after_approvals_too(self, paid, tenant, admin):
        refunds.approve_refund(req(paid, tenant, 15000), admin)
        with pytest.raises(ValidationError):
            req(paid, tenant, 5001)

    def test_validation(self, paid, tenant, stranger, landlord):
        with pytest.raises(PermissionDenied):
            req(paid, stranger, 100)
        with pytest.raises(ValidationError, match='reason'):
            req(paid, tenant, 100, ' ')
        with pytest.raises(ValidationError):
            req(paid, tenant, 0)
        with pytest.raises(PermissionDenied):
            req(paid, tenant, 20000, kind='reversal')                    # a customer cannot request a reversal
        Payment.objects.filter(pk=paid.pk).update(completed_at=timezone.now() - timedelta(days=400))
        paid.refresh_from_db()
        with pytest.raises(ValidationError, match='within'):
            req(paid, tenant, 100)
        Payment.objects.filter(pk=paid.pk).update(status='failed')
        paid.refresh_from_db()
        with pytest.raises(ValidationError, match='completed'):
            req(paid, tenant, 100)

    def test_reversal_is_full_amount_and_admin_only(self, paid, landlord, admin):
        with pytest.raises(ValidationError, match='full'):
            req(paid, landlord, 100, 'Duplicate', kind='reversal')
        r = req(paid, landlord, 20000, 'Duplicate payment', kind='reversal')
        assert r.approval_level == Refund.ApprovalLevel.ADMIN
        refunds.approve_refund(r, admin)
        paid.refresh_from_db()
        assert paid.status == Payment.Status.REFUNDED

    def test_wallet_that_already_paid_out_blocks_approval_unless_admin_allows_negative(self, paid, tenant, landlord, admin):
        debit_wallet(landlord, Decimal('19000'), 'Withdrawal')
        r = req(paid, tenant, 3000)
        with pytest.raises(ValidationError, match='withdrawn'):
            refunds.approve_refund(r, landlord)
        with pytest.raises(PermissionDenied):
            refunds.approve_refund(r, landlord, allow_negative_balance=True)   # only admins may override
        refunds.approve_refund(r, admin, allow_negative_balance=True)
        assert get_wallet_balance(landlord) == Decimal('-2850.00')
        paid.refresh_from_db()
        assert paid.refunded_amount == Decimal('3000')        # nothing was half-applied by the failed attempts

    def test_failed_approval_changes_nothing(self, paid, tenant, landlord):
        debit_wallet(landlord, Decimal('19000'), 'Withdrawal')
        r = req(paid, tenant, 3000)
        with pytest.raises(ValidationError):
            refunds.approve_refund(r, landlord)
        paid.refresh_from_db(); paid.invoice.refresh_from_db(); r.refresh_from_db()
        assert paid.refunded_amount == 0 and paid.invoice.amount_paid == Decimal('20000') and r.status == 'requested'

    def test_reject_cancel_and_double_decision(self, paid, tenant, landlord, admin):
        r = req(paid, tenant, 3000)
        with pytest.raises(ValidationError):
            refunds.reject_refund(r, landlord, ' ')
        refunds.reject_refund(r, landlord, 'Already refunded in cash')
        with pytest.raises(ValidationError, match='already'):
            refunds.approve_refund(r, admin)
        r2 = req(paid, tenant, 3000)
        with pytest.raises(PermissionDenied):
            refunds.cancel_refund(r2, landlord)
        refunds.cancel_refund(r2, tenant)
        assert Refund.objects.get(pk=r2.pk).status == Refund.Status.CANCELLED

    def test_payout_is_recorded_with_a_unique_reference(self, paid, tenant, admin):
        r = refunds.approve_refund(req(paid, tenant, 3000), admin)
        with pytest.raises(PermissionDenied):
            refunds.mark_refund_paid(r, tenant, 'QHX9PAYOUT1')
        with pytest.raises(ValidationError):
            refunds.mark_refund_paid(r, admin, 'x')
        r = refunds.mark_refund_paid(r, admin, 'QHX9PAYOUT1')
        assert r.status == Refund.Status.PAID_OUT and r.paid_out_by_id == admin.id
        r2 = refunds.approve_refund(req(paid, tenant, 1000), admin)
        with pytest.raises(ValidationError, match='already been used'):
            refunds.mark_refund_paid(r2, admin, 'qhx9payout1')

    def test_late_completion_callback_cannot_resurrect_a_refunded_payment(self, paid, tenant, admin):
        refunds.approve_refund(req(paid, tenant, 20000), admin)
        mark_payment_completed(paid, received_amount='20000')           # a duplicate callback arrives afterwards
        paid.invoice.refresh_from_db()
        assert paid.invoice.amount_paid == 0


@pytest.mark.django_db
class TestRefundApi:
    def test_full_flow_through_the_api_with_scoping(self, api_client, paid, tenant, landlord, admin, stranger):
        api_client.force_authenticate(user=tenant)
        r = api_client.post(f'/api/v1/payments/{paid.id}/refunds/', {'amount': '3000', 'reason': 'Double charged'}, format='json')
        assert r.status_code == 201, r.data
        rid = r.data['data']['id']
        assert r.data['data']['can_decide'] is False                      # requester cannot decide
        api_client.force_authenticate(user=stranger)
        assert api_client.get('/api/v1/refunds/').data['results'] == []
        assert api_client.post(f'/api/v1/refunds/{rid}/approve/').status_code == 404
        api_client.force_authenticate(user=landlord)
        listing = api_client.get('/api/v1/refunds/').data['results']
        assert [x['id'] for x in listing] == [rid] and listing[0]['can_decide'] is True
        assert api_client.post(f'/api/v1/refunds/{rid}/approve/', {'comment': 'ok'}, format='json').status_code == 200
        api_client.force_authenticate(user=admin)
        assert api_client.post(f'/api/v1/refunds/{rid}/mark-paid/', {'reference': 'QHX9PAYOUT2'}, format='json').data['data']['status'] == 'paid_out'
        assert api_client.post(f'/api/v1/refunds/{rid}/nonsense/').status_code == 404

    def test_api_errors_are_clear(self, api_client, paid, tenant):
        api_client.force_authenticate(user=tenant)
        r = api_client.post(f'/api/v1/payments/{paid.id}/refunds/', {'amount': '999999', 'reason': 'x'}, format='json')
        assert r.status_code == 400 and 'can still be refunded' in r.data['error']['message']
        assert api_client.post(f'/api/v1/payments/{paid.id}/refunds/', {'amount': '5'}, format='json').status_code == 400


# ===================================================================== reconciliation
TODAY = timezone.localdate()


@pytest.mark.django_db
class TestInternalReconciliation:
    def run(self):
        return recon.run_internal_checks(TODAY, TODAY)

    def test_clean_books_produce_no_issues(self, paid):
        run = self.run()
        assert run.rows_checked == 1 and run.issues == 0 and run.matched == 1

    def test_books_still_balance_after_refunds(self, paid, tenant, admin):
        refunds.approve_refund(req(paid, tenant, 3000), admin)
        refunds.approve_refund(req(paid, tenant, 17000), admin)
        assert self.run().issues == 0

    def test_missing_duplicate_and_wrong_wallet_amounts_are_found(self, paid, landlord):
        WalletTransaction.objects.filter(related_payment=paid).delete()
        assert list(self.run().items.values_list('kind', flat=True)) == [K.MISSING_WALLET_CREDIT]
        credit_wallet(landlord, Decimal('19000'), 'dup', related_payment=paid)
        credit_wallet(landlord, Decimal('19000'), 'dup2', related_payment=paid)
        assert K.DUPLICATE_WALLET_CREDIT in list(self.run().items.values_list('kind', flat=True))
        WalletTransaction.objects.filter(related_payment=paid).delete()
        credit_wallet(landlord, Decimal('500'), 'wrong amount', related_payment=paid)
        item = self.run().items.get()
        assert item.kind == K.WALLET_AMOUNT_MISMATCH and item.expected_amount == Decimal('19000.00') and item.actual_amount == Decimal('500.00')

    def test_disputed_stuck_and_unpaid_refunds_surface(self, paid, tenant, admin):
        d = Payment.objects.create(payer=tenant, amount=100, status='disputed', failure_reason='Amount mismatch')
        s = Payment.objects.create(payer=tenant, amount=200, status='pending')
        Payment.objects.filter(pk=s.pk).update(created_at=timezone.now() - timedelta(hours=3))
        r = refunds.approve_refund(req(paid, tenant, 3000), admin)
        Refund.objects.filter(pk=r.pk).update(decided_at=timezone.now() - timedelta(days=5))
        kinds = set(self.run().items.values_list('kind', flat=True))
        assert {K.DISPUTED_PAYMENT, K.STUCK_PAYMENT, K.UNPAID_REFUND} <= kinds


@pytest.mark.django_db
class TestStatementReconciliation:
    CSV = (
        'Statement for 600123\nGenerated 2026-03-31\n\n'
        'Receipt No.,Completion Time,Details,Paid In,Withdrawn,Balance\n'
        'QHX1ABC123,2026-03-10 10:00,Pay Bill from 254712345678,"20,000.00",,50000\n'
        'ZZZ9NOTHERE,2026-03-11 11:00,Pay Bill from 254722000000,"1,500.00",,51500\n'
        'CHG1,2026-03-12 11:00,Charges,,50.00,51450\n'
    )

    def test_parser_handles_title_lines_commas_and_non_receipt_lines(self):
        rows, skipped = recon.parse_statement_csv(self.CSV)
        assert rows == [{'receipt': 'QHX1ABC123', 'amount': Decimal('20000.00')},
                        {'receipt': 'ZZZ9NOTHERE', 'amount': Decimal('1500.00')}]
        assert skipped == 1
        with pytest.raises(ValidationError):
            recon.parse_statement_csv('foo,bar\n1,2\n')

    def test_matched_missing_and_mismatched_lines(self, paid):
        Payment.objects.filter(pk=paid.pk).update(completed_at=timezone.now())
        rows, _ = recon.parse_statement_csv(self.CSV)
        run = recon.reconcile_statement(rows, TODAY, TODAY)
        assert run.rows_checked == 2 and run.matched == 1
        item = run.items.get()
        assert item.kind == K.MISSING_IN_PLATFORM and item.receipt == 'ZZZ9NOTHERE' and item.actual_amount == Decimal('1500.00')

        rows[0]['amount'] = Decimal('19000.00')
        run = recon.reconcile_statement(rows, TODAY, TODAY)
        kinds = {i.kind for i in run.items.all()}
        assert K.AMOUNT_MISMATCH in kinds

        run = recon.reconcile_statement([{'receipt': 'ZZZ9NOTHERE', 'amount': Decimal('1500')}], TODAY, TODAY)
        assert K.MISSING_IN_STATEMENT in {i.kind for i in run.items.all()}      # platform has QHX1ABC123, statement lacks it

    def test_paybill_money_that_was_never_matched_is_reported(self, db):
        PaybillTransaction.objects.create(mpesa_receipt_number='PBL1XYZ777', amount=Decimal('900'),
                                          match_status='unmatched')
        run = recon.reconcile_statement([{'receipt': 'PBL1XYZ777', 'amount': Decimal('900')}], TODAY, TODAY)
        item = run.items.get()
        assert item.kind == K.MISSING_IN_PLATFORM and 'paybill' in item.note.lower()

    def test_upload_endpoint_is_admin_only_and_resolution_needs_a_note(self, api_client, paid, admin, landlord):
        Payment.objects.filter(pk=paid.pk).update(completed_at=timezone.now())
        f = lambda: SimpleUploadedFile('stmt.csv', self.CSV.encode(), content_type='text/csv')
        api_client.force_authenticate(user=landlord)
        assert api_client.post('/api/v1/reconciliation/runs/statement/', {'file': f()}, format='multipart').status_code == 403
        api_client.force_authenticate(user=admin)
        r = api_client.post('/api/v1/reconciliation/runs/statement/',
                            {'file': f(), 'period_start': str(TODAY), 'period_end': str(TODAY)}, format='multipart')
        assert r.status_code == 201 and r.data['data']['issues'] == 1 and r.data['data']['skipped_lines'] == 1
        detail = api_client.get(f"/api/v1/reconciliation/runs/{r.data['data']['id']}/").data['data']
        item_id = detail['items'][0]['id']
        assert api_client.post(f'/api/v1/reconciliation/items/{item_id}/resolve/', {'note': ' '}, format='json').status_code == 400
        ok = api_client.post(f'/api/v1/reconciliation/items/{item_id}/resolve/', {'note': 'Customer paid wrong account'}, format='json')
        assert ok.status_code == 200 and ok.data['data']['resolved'] is True
        assert api_client.post(f'/api/v1/reconciliation/items/{item_id}/resolve/', {'note': 'again'}, format='json').status_code == 400
        assert api_client.post('/api/v1/reconciliation/runs/statement/', {}, format='multipart').status_code == 400
        assert api_client.post('/api/v1/reconciliation/runs/statement/',
                               {'file': SimpleUploadedFile('x.csv', b'a,b\n1,2\n')}, format='multipart').status_code == 400

    def test_internal_run_endpoint_and_daily_task(self, api_client, paid, admin):
        api_client.force_authenticate(user=admin)
        r = api_client.post('/api/v1/reconciliation/runs/internal/', {'period_start': str(TODAY), 'period_end': str(TODAY)}, format='json')
        assert r.status_code == 201 and r.data['data']['issues'] == 0
        from apps.payments.tasks import run_daily_reconciliation
        assert 'run' in run_daily_reconciliation()


@pytest.mark.django_db
class TestSettlementSummary:
    def test_summary_reconciles_to_the_ledger(self, api_client, paid, tenant, landlord, admin):
        refunds.approve_refund(req(paid, tenant, 3000), admin)
        api_client.force_authenticate(user=admin)
        d = api_client.get(f'/api/v1/settlement/summary/?start={TODAY}&end={TODAY}').data['data']
        assert Decimal(str(d['gross_collected'])) == Decimal('20000.00')
        assert Decimal(str(d['credited_to_recipients'])) == Decimal('19000.00')
        assert Decimal(str(d['platform_commission'])) == Decimal('1000.00')
        assert Decimal(str(d['refunds_approved'])) == Decimal('3000.00')
        assert Decimal(str(d['refunds_awaiting_payout'])) == Decimal('3000.00')
        assert Decimal(str(d['recovered_from_recipient_wallets'])) == Decimal('2850.00')
        assert Decimal(str(d['wallet_liability'])) == Decimal('16150.00') == get_wallet_balance(landlord)
        api_client.force_authenticate(user=landlord)
        assert api_client.get('/api/v1/settlement/summary/').status_code == 403
