from rest_framework import serializers
from .models import Refund, ReconciliationItem, ReconciliationRun, Payment, MpesaTransaction, Payout, WalletTransaction, PaybillTransaction


class PaymentSerializer(serializers.ModelSerializer):
    payer_name = serializers.CharField(source='payer.get_full_name', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'payer', 'payer_name', 'invoice', 'booking', 'method', 'status',
            'amount', 'refunded_amount', 'phone_number', 'reference', 'description', 'failure_reason',
            'created_at', 'completed_at',
        ]
        read_only_fields = ['id', 'reference', 'status', 'failure_reason', 'created_at', 'completed_at']


class STKPushInitiateSerializer(serializers.Serializer):
    phone_number = serializers.RegexField(r'^(?:\+254|0)[17]\d{8}$')
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=1)
    invoice_id = serializers.UUIDField(required=False)
    booking_id = serializers.UUIDField(required=False)
    description = serializers.CharField(max_length=100, required=False, default="FRIDAH Payment")


class PayoutSerializer(serializers.ModelSerializer):
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)

    class Meta:
        model = Payout
        fields = [
            'id', 'recipient', 'recipient_name', 'amount', 'commission_amount',
            'phone_number', 'status', 'transaction_id', 'result_desc', 'created_at', 'completed_at',
        ]
        read_only_fields = fields


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = ['id', 'entry_type', 'amount', 'balance_after', 'description', 'created_at']


class PaybillTransactionSerializer(serializers.ModelSerializer):
    payer_name = serializers.SerializerMethodField()

    class Meta:
        model = PaybillTransaction
        fields = [
            'id', 'mpesa_receipt_number', 'amount', 'bill_ref_number', 'invoice_number',
            'msisdn', 'payer_name', 'match_status', 'matched_invoice', 'matched_payment',
            'reconciled_by', 'reconciled_at', 'created_at',
        ]
        read_only_fields = fields

    def get_payer_name(self, obj):
        return f"{obj.first_name} {obj.middle_name} {obj.last_name}".strip()


class ManualReconcileSerializer(serializers.Serializer):
    invoice_id = serializers.UUIDField()


from .models import PaymentMethod, PaymentAllocation, TenantAdvance, TenantAdvanceRepayment, ServiceProviderInvoice


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'method_type', 'label', 'phone_number', 'bank_name', 'account_number',
            'account_name', 'is_default', 'is_verified', 'created_at',
        ]
        read_only_fields = ['id', 'is_verified', 'created_at']


class PaymentAllocationSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)

    class Meta:
        model = PaymentAllocation
        fields = ['id', 'payment', 'invoice', 'invoice_number', 'amount', 'created_at']
        read_only_fields = fields


class TenantAdvanceSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.get_full_name', read_only=True)
    balance_outstanding = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = TenantAdvance
        fields = [
            'id', 'tenant', 'tenant_name', 'invoice', 'lease', 'amount', 'amount_repaid',
            'balance_outstanding', 'reason', 'status', 'approved_by', 'requested_at',
            'approved_at', 'due_date',
        ]
        read_only_fields = ['id', 'amount_repaid', 'status', 'approved_by', 'requested_at', 'approved_at']


class RequestTenantAdvanceSerializer(serializers.Serializer):
    lease_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=1)
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)
    invoice_id = serializers.UUIDField(required=False)


class TenantAdvanceRepaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantAdvanceRepayment
        fields = ['id', 'advance', 'payment', 'amount', 'created_at']
        read_only_fields = fields


class ServiceProviderInvoiceSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.get_full_name', read_only=True)

    class Meta:
        model = ServiceProviderInvoice
        fields = [
            'id', 'job', 'provider', 'provider_name', 'amount', 'description', 'attachment',
            'status', 'reviewed_by', 'review_notes', 'reviewed_at', 'payout', 'created_at',
        ]
        read_only_fields = ['id', 'status', 'reviewed_by', 'review_notes', 'reviewed_at', 'payout', 'created_at']


class SubmitServiceProviderInvoiceSerializer(serializers.Serializer):
    job_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=1)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)


class RefundSerializer(serializers.ModelSerializer):
    payment_reference = serializers.CharField(source='payment.reference', read_only=True)
    payment_amount = serializers.DecimalField(source='payment.amount', max_digits=12, decimal_places=2, read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True, default=None)
    decided_by_name = serializers.CharField(source='decided_by.get_full_name', read_only=True, default=None)
    can_decide = serializers.SerializerMethodField()
    auto_payout_available = serializers.SerializerMethodField()
    payout_status = serializers.SerializerMethodField()

    class Meta:
        model = Refund
        fields = [
            'id', 'payment', 'payment_reference', 'payment_amount', 'kind', 'amount', 'reason', 'status', 'approval_level',
            'requested_by', 'requested_by_name', 'decided_by', 'decided_by_name', 'decided_at', 'decision_comment',
            'recipient_debit', 'payout_reference', 'paid_out_at', 'created_at', 'can_decide',
            'auto_payout_available', 'payout_status',
        ]
        read_only_fields = fields

    def get_auto_payout_available(self, obj):
        from .refunds import auto_payout_enabled
        return auto_payout_enabled() and obj.status == Refund.Status.APPROVED

    def get_payout_status(self, obj):
        last = obj.payouts.order_by('-created_at').first()
        return last.status if last else None

    def get_can_decide(self, obj):
        """Whether the signed-in user may approve/reject this request right now (drives the UI buttons)."""
        request = self.context.get('request')
        if not request or obj.status != Refund.Status.REQUESTED:
            return False
        from .refunds import _check_can_decide
        try:
            _check_can_decide(obj, request.user)
            return True
        except Exception:
            return False


class ReconciliationItemSerializer(serializers.ModelSerializer):
    payment_reference = serializers.CharField(source='payment.reference', read_only=True, default=None)
    kind_label = serializers.CharField(source='get_kind_display', read_only=True)

    class Meta:
        model = ReconciliationItem
        fields = ['id', 'kind', 'kind_label', 'payment', 'payment_reference', 'receipt', 'expected_amount', 'actual_amount',
                  'note', 'resolved', 'resolution_note', 'resolved_at']
        read_only_fields = fields


class ReconciliationRunSerializer(serializers.ModelSerializer):
    open_issues = serializers.SerializerMethodField()

    class Meta:
        model = ReconciliationRun
        fields = ['id', 'source', 'period_start', 'period_end', 'file_name', 'rows_checked', 'matched', 'issues',
                  'open_issues', 'created_at']
        read_only_fields = fields

    def get_open_issues(self, obj):
        return obj.items.filter(resolved=False).count()
