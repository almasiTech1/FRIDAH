from django.contrib import admin
from .models import TaxType, TaxRule, TaxRecord, TaxAdjustment

admin.site.register(TaxType)
admin.site.register(TaxRule)


@admin.register(TaxRecord)
class TaxRecordAdmin(admin.ModelAdmin):
    list_display = ('owner', 'property', 'tax_type', 'period_start', 'period_end', 'calculated_amount', 'status')
    list_filter = ('status', 'tax_type')


@admin.register(TaxAdjustment)
class TaxAdjustmentAdmin(admin.ModelAdmin):
    list_display = ('record', 'actor', 'created_at')
    readonly_fields = [f.name for f in TaxAdjustment._meta.fields]
