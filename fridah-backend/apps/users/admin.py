from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, OTP, UserDevice, TenantBlacklistEntry


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'phone_number', 'role', 'kyc_status', 'is_active_account', 'created_at')
    list_filter = ('role', 'kyc_status', 'is_active_account', 'county')
    search_fields = ('username', 'email', 'phone_number', 'first_name', 'last_name')
    ordering = ('-created_at',)
    fieldsets = BaseUserAdmin.fieldsets + (
        ('FRIDAH Profile', {
            'fields': (
                'phone_number', 'role', 'national_id', 'kyc_status', 'kyc_document',
                'kyc_rejection_reason', 'is_phone_verified', 'is_email_verified',
                'county', 'town', 'profile_photo', 'business_name', 'service_category',
                'is_active_account',
            )
        }),
    )


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ('user', 'purpose', 'is_used', 'expires_at', 'created_at')
    list_filter = ('purpose', 'is_used')


@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display = ('user', 'platform', 'last_active')


@admin.register(TenantBlacklistEntry)
class TenantBlacklistEntryAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'flagged_by', 'reason', 'status', 'created_at')
    list_filter = ('status', 'reason')
    search_fields = ('tenant__username', 'tenant__phone_number')
