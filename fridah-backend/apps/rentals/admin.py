from django.contrib import admin
from .models import Lease, Invoice, MaintenanceRequest, MaintenanceImage, LeaseRenewal, UtilityAccount, UtilityMeterReading


@admin.register(Lease)
class LeaseAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'unit', 'landlord', 'status', 'rent_amount', 'start_date')
    list_filter = ('status',)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'tenant', 'invoice_type', 'amount', 'amount_paid', 'status', 'due_date')
    list_filter = ('status', 'invoice_type')
    search_fields = ('invoice_number',)


@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'tenant', 'unit', 'priority', 'status', 'created_at')
    list_filter = ('status', 'priority', 'category')


admin.site.register(MaintenanceImage)


@admin.register(LeaseRenewal)
class LeaseRenewalAdmin(admin.ModelAdmin):
    list_display = ('lease', 'status', 'proposed_rent_amount', 'proposed_end_date', 'created_at')
    list_filter = ('status',)


@admin.register(UtilityAccount)
class UtilityAccountAdmin(admin.ModelAdmin):
    list_display = ('unit', 'utility_type', 'is_metered', 'rate_per_unit', 'flat_monthly_fee', 'is_active')
    list_filter = ('utility_type', 'is_metered', 'is_active')


@admin.register(UtilityMeterReading)
class UtilityMeterReadingAdmin(admin.ModelAdmin):
    list_display = ('utility_account', 'reading_value', 'reading_date', 'generated_invoice', 'created_at')
    list_filter = ('utility_account__utility_type',)
