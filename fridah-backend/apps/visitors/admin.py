from django.contrib import admin
from .models import Visitor


@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ('visitor_name', 'unit', 'expected_date', 'status', 'checked_in_at', 'checked_out_at')
    list_filter = ('status', 'expected_date')
    search_fields = ('visitor_name', 'visitor_phone', 'qr_token')
