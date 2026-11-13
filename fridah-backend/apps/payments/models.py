import uuid
from django.db import models
from django.conf import settings
from common.private_files import service_invoice_path


class Payment(models.Model):
    class Method(models.TextChoices):
        MPESA_STK = 'mpesa_stk', 'M-Pesa STK Push'
        MPESA_C2B = 'mpesa_c2b', 'M-Pesa C2B'
        CASH = 'cash', 'Cash'
        BANK = 'bank', 'Bank Transfer'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'
        REVERSED = 'reversed', 'Reversed'
        REFUNDED = 'refunded', 'Refunded'
        DISPUTED = 'disputed', 'Disputed / amount mismatch'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    invoice = models.ForeignKey('rentals.Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    booking = models.ForeignKey('bookings.Booking', on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')

    method = models.CharField(max_length=20, choices=Method.choices, default=Method.MPESA_STK)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    phone_number = models.CharField(max_length=13, blank=True)

    reference = models.CharField(max_length=50, unique=True)  # internal ref
    description = models.CharField(max_length=255, blank=True)
    failure_reason = models.TextField(blank=True)
    # Total approved refunds/reversals against this payment (never exceeds `amount`).
    refunded_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'payments'
        indexes = [models.Index(fields=['status']), models.Index(fields=['reference'])]

    def __str__(self):
        return f"{self.reference} - {self.amount} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"PAY-{uuid.uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)


class MpesaTransaction(models.Model):
    """Raw record of every Daraja STK push request + callback for audit/reconciliation."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='mpesa_transaction')

    merchant_request_id = models.CharField(max_length=100, blank=True, null=True)
    checkout_request_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)

    mpesa_receipt_number = models.CharField(max_length=50, blank=True, null=True, unique=True)
    transaction_date = models.CharField(max_length=20, blank=True, null=True)
    phone_number = models.CharField(max_length=13)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    result_code = models.IntegerField(null=True, blank=True)
    result_desc = models.TextField(blank=True, null=True)

    raw_request = models.JSONField(default=dict, blank=True)
    raw_callback = models.JSONField(default=dict, blank=True)

    poll_count = models.PositiveSmallIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mpesa_transactions'


class Payout(models.Model):
    """B2C disbursement to landlords / service providers / hosts (after commission)."""
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payouts')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    phone_number = models.CharField(max_length=13)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    conversation_id = models.CharField(max_length=100, blank=True, null=True)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    result_code = models.IntegerField(null=True, blank=True)
    result_desc = models.TextField(blank=True, null=True)
    raw_callback = models.JSONField(default=dict, blank=True)

    related_payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name='payouts')
    # Set when this B2C disbursement pays a customer back for an approved refund (no recipient wallet is involved).
    refund = models.ForeignKey('payments.Refund', on_delete=models.SET_NULL, null=True, blank=True, related_name='payouts')

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'payouts'


class PaymentMethod(models.Model):
    """A saved payment method (M-Pesa number, bank account, card) so the payer doesn't
    have to retype it every time. FRIDAH launches M-Pesa-first, so `mpesa` is the
    common case; bank/card are captured for completeness/future use."""
    class MethodType(models.TextChoices):
        MPESA = 'mpesa', 'M-Pesa'
        BANK = 'bank', 'Bank Account'
        CARD = 'card', 'Card'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payment_methods')
    method_type = models.CharField(max_length=10, choices=MethodType.choices, default=MethodType.MPESA)
    label = models.CharField(max_length=100, blank=True)  # e.g. "My Safaricom line", "Equity current account"

    phone_number = models.CharField(max_length=13, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    account_name = models.CharField(max_length=150, blank=True)

    is_default = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payment_methods'
        indexes = [models.Index(fields=['user', 'is_default'])]

    def __str__(self):
        return f"{self.get_method_type_display()} - {self.label or self.phone_number or self.account_number}"

    def save(self, *args, **kwargs):
        if self.is_default:
            PaymentMethod.objects.filter(user=self.user, is_default=True).exclude(id=self.id).update(is_default=False)
        super().save(*args, **kwargs)


class PaymentAllocation(models.Model):
    """
    Splits one Payment across multiple Invoices (e.g. a tenant pays KES 25,000 which
    settles a 20,000 rent invoice plus a 5,000 penalty invoice; or a partial payment
    is allocated to the oldest outstanding invoice first). `Payment.invoice` remains
    the "primary" invoice for simple single-invoice payments; this table is the
    detailed breakdown whenever a payment needs to cover more than one.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='allocations')
    invoice = models.ForeignKey('rentals.Invoice', on_delete=models.CASCADE, related_name='payment_allocations')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payment_allocations'
        unique_together = ('payment', 'invoice')

    def __str__(self):
        return f"{self.payment.reference} -> {self.invoice.invoice_number}: KES {self.amount}"


class TenantAdvance(models.Model):
    """
    A rent-assistance advance extended to a tenant (by their landlord, managing agency,
    or the platform) to cover a shortfall, repayable via subsequent instalments. This is
    a ledger of assistance given, distinct from the wallet (which tracks landlord/provider
    earnings) and from Payout (which disburses money out to a recipient).
    """
    class Status(models.TextChoices):
        PENDING_APPROVAL = 'pending_approval', 'Pending Approval'
        ACTIVE = 'active', 'Active'
        REPAID = 'repaid', 'Fully Repaid'
        WRITTEN_OFF = 'written_off', 'Written Off'
        REJECTED = 'rejected', 'Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='advances')
    invoice = models.ForeignKey(
        'rentals.Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='advances'
    )
    lease = models.ForeignKey('rentals.Lease', on_delete=models.CASCADE, related_name='advances')

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_repaid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_APPROVAL)

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='advances_approved'
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)  # target date for full repayment

    class Meta:
        db_table = 'tenant_advances'
        indexes = [models.Index(fields=['tenant', 'status'])]

    def __str__(self):
        return f"Advance to {self.tenant} - KES {self.amount} ({self.status})"

    @property
    def balance_outstanding(self):
        return self.amount - self.amount_repaid


class TenantAdvanceRepayment(models.Model):
    """One instalment repaying a TenantAdvance, optionally linked to the Payment that funded it."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    advance = models.ForeignKey(TenantAdvance, on_delete=models.CASCADE, related_name='repayments')
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name='advance_repayments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tenant_advance_repayments'

    def __str__(self):
        return f"Repayment KES {self.amount} on {self.advance_id}"


class ServiceProviderInvoice(models.Model):
    """
    A service provider's invoice for a completed job, which must be approved before a
    Payout is triggered. This is the missing step between "job marked complete" and
    "provider gets paid" — separating the provider's claim for payment from its
    disbursement, and giving the payer (landlord/agency) a chance to review the amount.
    """
    class Status(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        APPROVED = 'approved', 'Approved'
        DISPUTED = 'disputed', 'Disputed'
        PAID = 'paid', 'Paid'
        REJECTED = 'rejected', 'Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey('services.ServiceJob', on_delete=models.CASCADE, related_name='invoices')
    provider = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='service_invoices')

    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    attachment = models.FileField(upload_to=service_invoice_path, blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='service_invoices_reviewed'
    )
    review_notes = models.CharField(max_length=255, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    payout = models.OneToOneField(
        Payout, on_delete=models.SET_NULL, null=True, blank=True, related_name='service_invoice'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'service_provider_invoices'
        indexes = [models.Index(fields=['provider', 'status'])]

    def __str__(self):
        return f"Invoice KES {self.amount} - {self.provider} ({self.status})"


class WalletTransaction(models.Model):
    """Ledger entry for in-app wallet balances (landlord/service-provider earnings)."""
    class EntryType(models.TextChoices):
        CREDIT = 'credit', 'Credit'
        DEBIT = 'debit', 'Debit'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet_transactions')
    entry_type = models.CharField(max_length=10, choices=EntryType.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    related_payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True)
    related_payout = models.ForeignKey(Payout, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wallet_transactions'


class PaybillTransaction(models.Model):
    """
    Every M-Pesa C2B confirmation received on FRIDAH's paybill, whether or not it could
    be automatically matched to an invoice. Tenants pay directly to the paybill using
    their invoice number as the account reference (no STK push involved), so this is the
    audit trail + reconciliation queue for those payments.
    """
    class MatchStatus(models.TextChoices):
        MATCHED = 'matched', 'Matched'
        UNMATCHED = 'unmatched', 'Unmatched - needs manual reconciliation'
        DUPLICATE = 'duplicate', 'Duplicate receipt (ignored)'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mpesa_receipt_number = models.CharField(max_length=50, unique=True)
    transaction_type = models.CharField(max_length=30, blank=True)
    transaction_time = models.CharField(max_length=20, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    business_short_code = models.CharField(max_length=20, blank=True)
    bill_ref_number = models.CharField(max_length=50, blank=True)  # AccountReference the payer typed in
    invoice_number = models.CharField(max_length=50, blank=True)  # normalized version used for matching
    msisdn = models.CharField(max_length=13, blank=True)
    first_name = models.CharField(max_length=100, blank=True)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)

    match_status = models.CharField(max_length=20, choices=MatchStatus.choices, default=MatchStatus.UNMATCHED)
    matched_invoice = models.ForeignKey(
        'rentals.Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='paybill_transactions'
    )
    matched_payment = models.OneToOneField(
        Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name='paybill_transaction'
    )
    reconciled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='manual_reconciliations',
    )
    reconciled_at = models.DateTimeField(null=True, blank=True)
    raw_callback = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'paybill_transactions'
        indexes = [
            models.Index(fields=['match_status']),
            models.Index(fields=['bill_ref_number']),
        ]

    def __str__(self):
        return f"{self.mpesa_receipt_number} - KES {self.amount} ({self.match_status})"


class Refund(models.Model):
    """
    A refund (customer asked for money back) or reversal (a mistaken/duplicate payment) against a
    completed payment. Maker-checker: the requester can never approve their own request; larger
    amounts and every reversal need a platform administrator. Approval immediately reverses the
    platform's books (invoice allocations, booking, recipient wallet); paying the customer back
    through M-Pesa is then recorded with its reference.
    """
    class Kind(models.TextChoices):
        REFUND = 'refund', 'Refund'
        REVERSAL = 'reversal', 'Reversal (mistaken / duplicate payment)'

    class Status(models.TextChoices):
        REQUESTED = 'requested', 'Awaiting approval'
        APPROVED = 'approved', 'Approved - payout to customer pending'
        PAID_OUT = 'paid_out', 'Paid out to customer'
        REJECTED = 'rejected', 'Rejected'
        CANCELLED = 'cancelled', 'Cancelled by requester'

    class ApprovalLevel(models.TextChoices):
        RECIPIENT = 'recipient', 'Recipient (landlord/host) or administrator'
        ADMIN = 'admin', 'Administrator only'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name='refunds')
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.REFUND)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.REQUESTED)
    approval_level = models.CharField(max_length=10, choices=ApprovalLevel.choices, default=ApprovalLevel.ADMIN)

    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_comment = models.TextField(blank=True)

    # Ledger effect recorded when approved (so it can be audited and reconciled)
    recipient_debit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ledger_applied_at = models.DateTimeField(null=True, blank=True)

    payout_reference = models.CharField(max_length=100, blank=True)
    paid_out_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    paid_out_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'refunds'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status']), models.Index(fields=['payment'])]

    def __str__(self):
        return f'{self.kind} {self.amount} on {self.payment_id} ({self.status})'


class ReconciliationRun(models.Model):
    """One reconciliation pass: either the platform's own consistency checks or a Safaricom statement upload."""
    class Source(models.TextChoices):
        INTERNAL = 'internal', 'Internal consistency checks'
        STATEMENT = 'statement', 'Safaricom statement upload'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.CharField(max_length=10, choices=Source.choices)
    period_start = models.DateField()
    period_end = models.DateField()
    file_name = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    rows_checked = models.PositiveIntegerField(default=0)
    matched = models.PositiveIntegerField(default=0)
    issues = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reconciliation_runs'
        ordering = ['-created_at']


class ReconciliationItem(models.Model):
    """One discrepancy found by a run. Stays open until an administrator resolves it with a note."""
    class Kind(models.TextChoices):
        AMOUNT_MISMATCH = 'amount_mismatch', 'Amount differs from statement'
        MISSING_IN_PLATFORM = 'missing_in_platform', 'In statement but not recorded on the platform'
        MISSING_IN_STATEMENT = 'missing_in_statement', 'Recorded on the platform but not in statement'
        MISSING_WALLET_CREDIT = 'missing_wallet_credit', 'Completed payment without a wallet credit'
        DUPLICATE_WALLET_CREDIT = 'duplicate_wallet_credit', 'Wallet credited more than once'
        WALLET_AMOUNT_MISMATCH = 'wallet_amount_mismatch', 'Wallet total does not match the payment'
        STUCK_PAYMENT = 'stuck_payment', 'Payment stuck pending/processing'
        DISPUTED_PAYMENT = 'disputed_payment', 'Disputed payment awaiting a decision'
        UNPAID_REFUND = 'unpaid_refund', 'Approved refund not yet paid out'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(ReconciliationRun, on_delete=models.CASCADE, related_name='items')
    kind = models.CharField(max_length=30, choices=Kind.choices)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    receipt = models.CharField(max_length=50, blank=True)
    expected_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    actual_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)
    resolved = models.BooleanField(default=False)
    resolution_note = models.TextField(blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reconciliation_items'
        ordering = ['created_at']
        indexes = [models.Index(fields=['resolved'])]


class RefundPolicy(models.Model):
    """
    Finance-controlled refund limits, editable by an administrator (every change is audited).
    A single row; when none exists the values from settings / .env apply. Whether people may approve
    their own requests is deliberately NOT editable here - it stays an environment setting.
    """
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    admin_approval_above = models.DecimalField(max_digits=12, decimal_places=2)
    window_days = models.PositiveSmallIntegerField()
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'refund_policy'
