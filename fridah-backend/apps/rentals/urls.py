from django.urls import path
from . import views

urlpatterns = [
    path('leases/', views.LeaseListCreateView.as_view(), name='lease_list'),
    path('leases/<uuid:id>/', views.LeaseDetailView.as_view(), name='lease_detail'),
    path('leases/<uuid:id>/activate/', views.LeaseActivateView.as_view(), name='lease_activate'),
    path('leases/<uuid:id>/terminate/', views.LeaseTerminateView.as_view(), name='lease_terminate'),

    path('invoices/', views.InvoiceListView.as_view(), name='invoice_list'),
    path('invoices/<uuid:id>/', views.InvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoices/<uuid:id>/waive/', views.AmenityInvoiceWaiveView.as_view(), name='invoice_waive'),
    path('amenity-charges/', views.AmenityChargeListCreateView.as_view(), name='amenity_charges'),
    path('amenity-charges/<uuid:id>/', views.AmenityChargeDetailView.as_view(), name='amenity_charge_detail'),
    path('amenity-charges/<uuid:id>/bill-now/', views.AmenityBillNowView.as_view(), name='amenity_bill_now'),
    path('amenity-exemptions/', views.AmenityExemptionCreateView.as_view(), name='amenity_exemptions'),

    path('maintenance/', views.MaintenanceRequestListCreateView.as_view(), name='maintenance_list'),
    path('maintenance/<uuid:id>/', views.MaintenanceRequestDetailView.as_view(), name='maintenance_detail'),
    path('maintenance/<uuid:id>/assign/', views.MaintenanceAssignView.as_view(), name='maintenance_assign'),
    path('maintenance/<uuid:id>/resolve/', views.MaintenanceResolveView.as_view(), name='maintenance_resolve'),
    path('maintenance/<uuid:id>/images/', views.MaintenanceImageUploadView.as_view(), name='maintenance_image_upload'),

    path('lease-renewals/', views.LeaseRenewalListView.as_view(), name='lease_renewal_list'),
    path('lease-renewals/<uuid:id>/', views.LeaseRenewalDetailView.as_view(), name='lease_renewal_detail'),
    path('lease-renewals/<uuid:id>/respond/', views.LeaseRenewalRespondView.as_view(), name='lease_renewal_respond'),
]

# Digital lease signing
from .signing_views import LeaseSignatureStatusView, LeaseInitiateSigningView, LeaseSignView
urlpatterns += [
    path('leases/<uuid:lease_id>/signature/', LeaseSignatureStatusView.as_view(), name='lease_signature_status'),
    path('leases/<uuid:lease_id>/signature/initiate/', LeaseInitiateSigningView.as_view(), name='lease_initiate_signing'),
    path('leases/<uuid:lease_id>/signature/sign/', LeaseSignView.as_view(), name='lease_sign'),
]

urlpatterns += [
    path('utility-accounts/', views.UtilityAccountListCreateView.as_view(), name='utility_account_list'),
    path('utility-accounts/<uuid:id>/', views.UtilityAccountDetailView.as_view(), name='utility_account_detail'),
    path('utility-readings/', views.UtilityMeterReadingListCreateView.as_view(), name='utility_reading_list'),
]

urlpatterns += [
    path('units/<uuid:unit_id>/apply/', views.UnitApplyView.as_view(), name='unit_apply'),
    path('rental-applications/', views.RentalApplicationListView.as_view(), name='rental_application_list'),
    path('rental-applications/<uuid:id>/approve/', views.RentalApplicationApproveView.as_view(), name='rental_application_approve'),
    path('rental-applications/<uuid:id>/reject/', views.RentalApplicationRejectView.as_view(), name='rental_application_reject'),
    path('rental-applications/<uuid:id>/withdraw/', views.RentalApplicationWithdrawView.as_view(), name='rental_application_withdraw'),
]
