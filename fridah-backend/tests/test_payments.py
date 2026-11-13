from decimal import Decimal
from datetime import date

import pytest

from apps.rentals.models import Invoice
from apps.payments.models import Payment, PaymentAllocation, TenantAdvance
from apps.payments import services as payment_services


@pytest.mark.django_db
class TestPaymentAllocation:
    def test_overpayment_sweeps_to_next_invoice(self, tenant, landlord, lease):
        rent_invoice = Invoice.objects.create(
            lease=lease, tenant=tenant, invoice_type='rent', amount=Decimal('15000'),
            period_start=date(2026, 2, 1), period_end=date(2026, 2, 28), due_date=date(2026, 2, 5),
        )
        penalty_invoice = Invoice.objects.create(
            lease=lease, tenant=tenant, invoice_type='penalty', amount=Decimal('1500'),
            period_start=date(2026, 2, 1), period_end=date(2026, 2, 28), due_date=date(2026, 2, 5),
        )
        payment = Payment.objects.create(
            payer=tenant, invoice=rent_invoice, amount=Decimal('16500'), method=Payment.Method.MPESA_STK,
            status=Payment.Status.PENDING, phone_number=tenant.phone_number,
        )
        payment_services.mark_payment_completed(payment)

        rent_invoice.refresh_from_db()
        penalty_invoice.refresh_from_db()
        assert rent_invoice.status == Invoice.Status.PAID
        assert penalty_invoice.status == Invoice.Status.PAID
        assert penalty_invoice.amount_paid == Decimal('1500')

        allocations = PaymentAllocation.objects.filter(payment=payment)
        assert allocations.count() == 2


@pytest.mark.django_db
class TestTenantAdvance:
    def test_advance_request_starts_pending_approval(self, tenant, lease):
        invoice = Invoice.objects.create(
            lease=lease, tenant=tenant, invoice_type='rent', amount=Decimal('15000'),
            period_start=date(2026, 3, 1), period_end=date(2026, 3, 31), due_date=date(2026, 3, 5),
        )
        advance = payment_services.request_tenant_advance(
            tenant=tenant, lease=lease, amount=Decimal('15000'), reason='Short this month', invoice=invoice,
        )
        assert advance.status == TenantAdvance.Status.PENDING_APPROVAL

    def test_approving_advance_pays_the_invoice(self, tenant, landlord, lease):
        invoice = Invoice.objects.create(
            lease=lease, tenant=tenant, invoice_type='rent', amount=Decimal('15000'),
            period_start=date(2026, 3, 1), period_end=date(2026, 3, 31), due_date=date(2026, 3, 5),
        )
        advance = payment_services.request_tenant_advance(
            tenant=tenant, lease=lease, amount=Decimal('15000'), reason='Short this month', invoice=invoice,
        )
        advance = payment_services.approve_tenant_advance(advance, approved_by=landlord)
        invoice.refresh_from_db()
        assert invoice.status == Invoice.Status.PAID
        assert advance.status == TenantAdvance.Status.ACTIVE

    def test_repayment_accumulates_and_completes(self, tenant, landlord, lease):
        invoice = Invoice.objects.create(
            lease=lease, tenant=tenant, invoice_type='rent', amount=Decimal('15000'),
            period_start=date(2026, 3, 1), period_end=date(2026, 3, 31), due_date=date(2026, 3, 5),
        )
        advance = payment_services.request_tenant_advance(
            tenant=tenant, lease=lease, amount=Decimal('15000'), reason='Short this month', invoice=invoice,
        )
        advance = payment_services.approve_tenant_advance(advance, approved_by=landlord)

        advance = payment_services.repay_tenant_advance(advance, amount=Decimal('7500'))
        assert advance.amount_repaid == Decimal('7500')
        assert advance.status == TenantAdvance.Status.ACTIVE

        advance = payment_services.repay_tenant_advance(advance, amount=Decimal('7500'))
        assert advance.amount_repaid == Decimal('15000')
        assert advance.status == TenantAdvance.Status.REPAID
