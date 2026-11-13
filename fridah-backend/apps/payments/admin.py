from django.contrib import admin
from .models import Payment, MpesaTransaction, Payout, WalletTransaction, PaybillTransaction


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('reference', 'payer', 'method', 'amount', 'status', 'created_at')
    list_filter = ('status', 'method')
    search_fields = ('reference',)


@admin.register(MpesaTransaction)
class MpesaTransactionAdmin(admin.ModelAdmin):
    list_display = ('checkout_request_id', 'mpesa_receipt_number', 'amount', 'result_code', 'created_at')
    search_fields = ('checkout_request_id', 'mpesa_receipt_number')


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'amount', 'status', 'transaction_id', 'created_at')
    list_filter = ('status',)


admin.site.register(WalletTransaction)


@admin.register(PaybillTransaction)
class PaybillTransactionAdmin(admin.ModelAdmin):
    list_display = ('mpesa_receipt_number', 'amount', 'bill_ref_number', 'match_status', 'created_at')
    list_filter = ('match_status',)
    search_fields = ('mpesa_receipt_number', 'bill_ref_number', 'msisdn')


from .models import PaymentMethod, PaymentAllocation, TenantAdvance, TenantAdvanceRepayment, ServiceProviderInvoice

admin.site.register(PaymentMethod)
admin.site.register(PaymentAllocation)


@admin.register(TenantAdvance)
class TenantAdvanceAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'amount', 'amount_repaid', 'status', 'requested_at')
    list_filter = ('status',)


admin.site.register(TenantAdvanceRepayment)


@admin.register(ServiceProviderInvoice)
class ServiceProviderInvoiceAdmin(admin.ModelAdmin):
    list_display = ('provider', 'job', 'amount', 'status', 'created_at')
    list_filter = ('status',)
