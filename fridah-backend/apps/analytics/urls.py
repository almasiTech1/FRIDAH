from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/tenant/', views.TenantDashboardView.as_view(), name='dashboard_tenant'),
    path('dashboard/landlord/', views.LandlordDashboardView.as_view(), name='dashboard_landlord'),
    path('dashboard/service-provider/', views.ServiceProviderDashboardView.as_view(), name='dashboard_service_provider'),
    path('dashboard/hotel-owner/', views.HotelOwnerDashboardView.as_view(), name='dashboard_hotel_owner'),
    path('dashboard/admin/', views.AdminDashboardView.as_view(), name='dashboard_admin'),
    path('dashboard/admin/portfolio/', views.AdminPortfolioView.as_view(), name='dashboard_admin_portfolio'),
]

# Advanced analytics
from .advanced_views import VacancyAnalyticsView, MarketBenchmarkView, RentForecastView, BulkInvoiceGenerationView, MaintenanceAnalyticsView, LeasingFunnelAnalyticsView, RevenueForecastView
urlpatterns += [
    path('analytics/vacancy/', VacancyAnalyticsView.as_view(), name='vacancy_analytics'),
    path('analytics/market-benchmark/', MarketBenchmarkView.as_view(), name='market_benchmark'),
    path('analytics/rent-forecast/', RentForecastView.as_view(), name='rent_forecast'),
    path('analytics/bulk-invoices/', BulkInvoiceGenerationView.as_view(), name='bulk_invoices'),
    path('analytics/maintenance/', MaintenanceAnalyticsView.as_view(), name='maintenance_analytics'),
    path('analytics/leasing-funnel/', LeasingFunnelAnalyticsView.as_view(), name='leasing_funnel_analytics'),
    path('analytics/revenue-forecast/', RevenueForecastView.as_view(), name='revenue_forecast'),
]

from .risk_views import TenantRiskScoreView
urlpatterns += [
    path('risk-score/<uuid:tenant_id>/', TenantRiskScoreView.as_view(), name='tenant_risk_score'),
]
