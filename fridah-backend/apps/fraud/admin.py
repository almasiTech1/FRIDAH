from django.contrib import admin
from .models import FraudFlag


@admin.register(FraudFlag)
class FraudFlagAdmin(admin.ModelAdmin):
    list_display = ('flag_type', 'subject_type', 'subject_id', 'status', 'created_at')
    list_filter = ('flag_type', 'status', 'subject_type')
    search_fields = ('subject_id', 'reason')
