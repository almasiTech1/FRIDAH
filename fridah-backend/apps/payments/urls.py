from django.urls import path
from . import views

urlpatterns = [
    path('payments/', views.PaymentListView.as_view(), name='payment_list'),
    path('payments/<uuid:id>/refunds/', views.RefundRequestView.as_view(), name='refund_request'),
    path('refunds/policy/', views.RefundPolicyView.as_view(), name='refund_policy'),
    path('refunds/', views.RefundListView.as_view(), name='refund_list'),
    path('refunds/<uuid:id>/<str:action>/', views.RefundActionView.as_view(), name='refund_action'),
    path('reconciliation/runs/', views.ReconciliationRunListView.as_view(), name='reconciliation_runs'),
    path('reconciliation/runs/internal/', views.RunInternalReconciliationView.as_view(), name='reconciliation_internal'),
    path('reconciliation/runs/statement/', views.UploadStatementView.as_view(), name='reconciliation_statement'),
    path('reconciliation/runs/<uuid:id>/', views.ReconciliationRunDetailView.as_view(), name='reconciliation_run'),
    path('reconciliation/items/<uuid:id>/resolve/', views.ResolveReconciliationItemView.as_view(), name='reconciliation_resolve'),
    path('settlement/summary/', views.SettlementSummaryView.as_view(), name='settlement_summary'),
    path('payments/<uuid:id>/resolve-dispute/', views.ResolveDisputedPaymentView.as_view(), name='resolve_dispute'),
    path('payments/mpesa/stk-push/', views.STKPushInitiateView.as_view(), name='stk_push'),
    path('payments/mpesa/status/<uuid:payment_id>/', views.STKPushStatusView.as_view(), name='stk_status'),
    path('payments/mpesa/stk-callback/', views.MpesaSTKCallbackView.as_view(), name='mpesa_stk_callback'),
    path('payments/mpesa/c2b-validation/', views.MpesaC2BValidationView.as_view(), name='mpesa_c2b_validation'),
    path('payments/mpesa/c2b-confirmation/', views.MpesaC2BConfirmationView.as_view(), name='mpesa_c2b_confirmation'),
    path('payments/mpesa/b2c-result/', views.MpesaB2CResultView.as_view(), name='mpesa_b2c_result'),
    path('payments/mpesa/b2c-timeout/', views.MpesaB2CTimeoutView.as_view(), name='mpesa_b2c_timeout'),

    path('wallet/', views.WalletBalanceView.as_view(), name='wallet_balance'),
    path('payouts/', views.PayoutListView.as_view(), name='payout_list'),
    path('payouts/request/', views.PayoutRequestView.as_view(), name='payout_request'),

    path('paybill-transactions/', views.PaybillTransactionListView.as_view(), name='paybill_transaction_list'),
    path(
        'paybill-transactions/<uuid:transaction_id>/reconcile/',
        views.PaybillTransactionReconcileView.as_view(), name='paybill_transaction_reconcile',
    ),

    path('payment-methods/', views.PaymentMethodListCreateView.as_view(), name='payment_method_list'),
    path('payment-methods/<uuid:id>/', views.PaymentMethodDeleteView.as_view(), name='payment_method_delete'),
    path('payments/<uuid:payment_id>/allocations/', views.PaymentAllocationListView.as_view(), name='payment_allocation_list'),

    path('tenant-advances/', views.TenantAdvanceListCreateView.as_view(), name='tenant_advance_list'),
    path('tenant-advances/<uuid:id>/approve/', views.TenantAdvanceApproveView.as_view(), name='tenant_advance_approve'),
    path('tenant-advances/<uuid:id>/reject/', views.TenantAdvanceRejectView.as_view(), name='tenant_advance_reject'),

    path('receipts/verify/', views.ReceiptVerifyView.as_view(), name='receipt_verify'),
    path('service-invoices/', views.ServiceProviderInvoiceListCreateView.as_view(), name='service_invoice_list'),
    path('service-invoices/<uuid:id>/approve/', views.ServiceProviderInvoiceApproveView.as_view(), name='service_invoice_approve'),
    path('service-invoices/<uuid:id>/reject/', views.ServiceProviderInvoiceRejectView.as_view(), name='service_invoice_reject'),
    path('service-invoices/<uuid:id>/pay/', views.ServiceProviderInvoicePayView.as_view(), name='service_invoice_pay'),
]
