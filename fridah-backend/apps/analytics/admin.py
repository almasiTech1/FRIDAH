from django.contrib import admin
from .models import DashboardSnapshot, PlatformMetric, TenantRiskScore


@admin.register(PlatformMetric)
class PlatformMetricAdmin(admin.ModelAdmin):
    list_display = ('metric_date', 'total_users', 'total_revenue', 'total_commission', 'active_leases', 'active_bookings')


admin.site.register(DashboardSnapshot)


@admin.register(TenantRiskScore)
class TenantRiskScoreAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'score', 'on_time_payment_rate', 'has_blacklist_flags', 'computed_at')
    list_filter = ('score', 'has_blacklist_flags')
