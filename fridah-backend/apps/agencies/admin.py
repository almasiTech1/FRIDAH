from django.contrib import admin
from .models import (
    Agency, AgencyRole, AgencyMembership, PropertyManagementAssignment, PropertyStaffAssignment,
    AgencyFeeRule, ManagementAgreement, OwnerStatement, OwnerPayout, AgencyCommission,
    AgencyExpense, AgencyAuditLog,
)


@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'default_fee_percent', 'managed_properties_count', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'registration_number', 'email')


@admin.register(AgencyRole)
class AgencyRoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'agency', 'role_type')
    list_filter = ('role_type',)


@admin.register(AgencyMembership)
class AgencyMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'agency', 'role', 'status', 'joined_at')
    list_filter = ('status',)


@admin.register(PropertyManagementAssignment)
class PropertyManagementAssignmentAdmin(admin.ModelAdmin):
    list_display = ('property', 'agency', 'status', 'start_date', 'end_date', 'management_fee_percent')
    list_filter = ('status',)


@admin.register(PropertyStaffAssignment)
class PropertyStaffAssignmentAdmin(admin.ModelAdmin):
    list_display = ('property', 'membership', 'is_active', 'assigned_at')
    list_filter = ('is_active',)


@admin.register(AgencyFeeRule)
class AgencyFeeRuleAdmin(admin.ModelAdmin):
    list_display = ('agency', 'name', 'fee_type', 'fee_value', 'is_default')


@admin.register(ManagementAgreement)
class ManagementAgreementAdmin(admin.ModelAdmin):
    list_display = ('property', 'agency', 'owner', 'status', 'start_date', 'end_date')
    list_filter = ('status',)


@admin.register(OwnerStatement)
class OwnerStatementAdmin(admin.ModelAdmin):
    list_display = ('property', 'owner', 'period_start', 'period_end', 'net_payable', 'status')
    list_filter = ('status',)


@admin.register(OwnerPayout)
class OwnerPayoutAdmin(admin.ModelAdmin):
    list_display = ('reference', 'owner', 'amount', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(AgencyCommission)
class AgencyCommissionAdmin(admin.ModelAdmin):
    list_display = ('agency', 'property', 'period_start', 'period_end', 'commission_amount')


@admin.register(AgencyExpense)
class AgencyExpenseAdmin(admin.ModelAdmin):
    list_display = ('property', 'agency', 'category', 'amount', 'incurred_on')
    list_filter = ('category',)


@admin.register(AgencyAuditLog)
class AgencyAuditLogAdmin(admin.ModelAdmin):
    list_display = ('agency', 'actor', 'action', 'created_at')
    list_filter = ('action',)
    readonly_fields = [f.name for f in AgencyAuditLog._meta.fields]
