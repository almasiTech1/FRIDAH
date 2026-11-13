from django.urls import path
from . import views

urlpatterns = [
    path('property-search/', views.PropertyAssistantSearchView.as_view(), name='ai_property_search'),
    path('rent-estimate/', views.RentEstimatorView.as_view(), name='ai_rent_estimate'),
    path('generate-listing/', views.ListingGeneratorView.as_view(), name='ai_generate_listing'),
    path('maintenance-triage/', views.MaintenanceTriageView.as_view(), name='ai_maintenance_triage'),
    path('usage-dashboard/', views.AIUsageDashboardView.as_view(), name='ai_usage_dashboard'),
    path('lease-drafting/', views.LeaseDraftingView.as_view(), name='ai_lease_drafting'),
]
