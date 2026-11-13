import os, django, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from decimal import Decimal
from datetime import date
from django.utils import timezone

from apps.users.models import User
from apps.properties.models import Property, Unit
from apps.rentals.models import Lease, Invoice
from apps.payments.models import Payment, PaymentAllocation, TenantAdvance, ServiceProviderInvoice, Payout
from apps.payments import services as payment_services
from apps.services.models import ServiceCategory, ServiceJob

print("=== Fixtures ===")
landlord = User.objects.create_user(username='pl_landlord', email='pl_landlord@test.com', password='x', role='landlord', phone_number='+254711000001')
tenant = User.objects.create_user(username='pl_tenant', email='pl_tenant@test.com', password='x', role='tenant', phone_number='+254711000002')
provider = User.objects.create_user(username='pl_provider', email='pl_provider@test.com', password='x', role='service_provider', phone_number='+254711000003')

prop = Property.objects.create(landlord=landlord, name='Palm Court', property_type='apartment', county='Nairobi', town='Kilimani', address_detail='45 Rd')
unit = Unit.objects.create(property=prop, unit_number='B2', rent_amount=Decimal('15000'), bedrooms=1, bathrooms=1)
lease = Lease.objects.create(unit=unit, tenant=tenant, landlord=landlord, rent_amount=Decimal('15000'), deposit_amount=Decimal('15000'), start_date=date(2026, 1, 1), rent_due_day=5, status='active')

rent_invoice = Invoice.objects.create(lease=lease, tenant=tenant, invoice_type='rent', amount=Decimal('15000'), period_start=date(2026, 2, 1), period_end=date(2026, 2, 28), due_date=date(2026, 2, 5))
penalty_invoice = Invoice.objects.create(lease=lease, tenant=tenant, invoice_type='penalty', amount=Decimal('1500'), period_start=date(2026, 2, 1), period_end=date(2026, 2, 28), due_date=date(2026, 2, 5))

print("=== Multi-invoice payment allocation (overpayment sweeps to penalty invoice) ===")
payment = Payment.objects.create(
    payer=tenant, invoice=rent_invoice, amount=Decimal('16500'), method=Payment.Method.MPESA_STK,
    status=Payment.Status.PENDING, phone_number=tenant.phone_number,
)
payment_services.mark_payment_completed(payment)

rent_invoice.refresh_from_db()
penalty_invoice.refresh_from_db()
print("Rent invoice status:", rent_invoice.status, rent_invoice.amount_paid)
print("Penalty invoice status:", penalty_invoice.status, penalty_invoice.amount_paid)
assert rent_invoice.status == Invoice.Status.PAID
assert penalty_invoice.status == Invoice.Status.PAID
assert penalty_invoice.amount_paid == Decimal('1500')
allocations = PaymentAllocation.objects.filter(payment=payment)
assert allocations.count() == 2, f"Expected 2 allocations, got {allocations.count()}"
print("Allocations created:", [(a.invoice.invoice_number, str(a.amount)) for a in allocations])

print("=== Tenant advance request + approval ===")
march_invoice = Invoice.objects.create(lease=lease, tenant=tenant, invoice_type='rent', amount=Decimal('15000'), period_start=date(2026, 3, 1), period_end=date(2026, 3, 31), due_date=date(2026, 3, 5))
advance = payment_services.request_tenant_advance(tenant=tenant, lease=lease, amount=Decimal('15000'), reason="Short this month", invoice=march_invoice)
assert advance.status == TenantAdvance.Status.PENDING_APPROVAL
advance = payment_services.approve_tenant_advance(advance, approved_by=landlord)
march_invoice.refresh_from_db()
print("March invoice after advance approval:", march_invoice.status, march_invoice.amount_paid)
assert march_invoice.status == Invoice.Status.PAID
assert advance.status == TenantAdvance.Status.ACTIVE

print("=== Advance repayment ===")
advance = payment_services.repay_tenant_advance(advance, amount=Decimal('7500'))
assert advance.amount_repaid == Decimal('7500')
assert advance.status == TenantAdvance.Status.ACTIVE
advance = payment_services.repay_tenant_advance(advance, amount=Decimal('7500'))
assert advance.status == TenantAdvance.Status.REPAID
print("Advance fully repaid:", advance.status)

print("=== Service provider invoicing + approval + payout ===")
category = ServiceCategory.objects.create(name='Plumbing')
job = ServiceJob.objects.create(
    posted_by=landlord, category=category, title='Fix leaking pipe', description='Kitchen sink leak',
    county='Nairobi', town='Kilimani', assigned_provider=provider, status=ServiceJob.Status.COMPLETED,
)
invoice = payment_services.submit_service_provider_invoice(job=job, provider=provider, amount=Decimal('3500'), description='Parts + labor')
assert invoice.status == ServiceProviderInvoice.Status.SUBMITTED
invoice = payment_services.approve_service_provider_invoice(invoice, reviewed_by=landlord, notes='Looks good')
assert invoice.status == ServiceProviderInvoice.Status.APPROVED

payout = payment_services.pay_service_provider_invoice(invoice, initiated_by=landlord)
invoice.refresh_from_db()
print("Service invoice status:", invoice.status, "| Payout:", payout.amount, payout.status)
assert invoice.status == ServiceProviderInvoice.Status.PAID
assert payout.amount == Decimal('3500')
assert payout.recipient_id == provider.id

print("\nALL PAYMENT ENGINE SMOKE TESTS PASSED")
