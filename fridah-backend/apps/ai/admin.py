from django.contrib import admin
from .models import AIInteractionLog


@admin.register(AIInteractionLog)
class AIInteractionLogAdmin(admin.ModelAdmin):
    list_display = ('feature', 'user', 'model', 'input_tokens', 'output_tokens', 'succeeded', 'latency_ms', 'created_at')
    list_filter = ('feature', 'succeeded', 'model')
    search_fields = ('user__email', 'user__username')
    readonly_fields = [f.name for f in AIInteractionLog._meta.fields]

    def has_add_permission(self, request):
        return False
