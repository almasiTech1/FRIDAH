from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'actor', 'target_type', 'property', 'severity', 'created_at')
    list_filter = ('severity', 'action')
    search_fields = ('action', 'target_type', 'target_id')
    readonly_fields = [f.name for f in AuditLog._meta.fields]
