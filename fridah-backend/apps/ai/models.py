import uuid
from django.db import models
from django.conf import settings


class AIInteractionLog(models.Model):
    """
    Every call out to Claude for an AI feature, logged for cost visibility and abuse
    monitoring. Not used to gate functionality - purely observability.
    """
    class Feature(models.TextChoices):
        PROPERTY_ASSISTANT = 'property_assistant', 'AI Property Assistant'
        RENT_ESTIMATOR = 'rent_estimator', 'AI Rent Estimator'
        LISTING_GENERATOR = 'listing_generator', 'AI Listing Generator'
        MAINTENANCE_TRIAGE = 'maintenance_triage', 'AI Maintenance Assistant'
        STATEMENT_SUMMARY = 'statement_summary', 'AI Owner Statement Summary'
        LEASE_DRAFTING = 'lease_drafting', 'AI Lease Drafting Assistant'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_interactions'
    )
    feature = models.CharField(max_length=30, choices=Feature.choices)
    model = models.CharField(max_length=50)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    succeeded = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    latency_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_interaction_logs'
        indexes = [
            models.Index(fields=['feature', 'created_at']),
        ]

    def __str__(self):
        return f"{self.feature} by {self.user} ({'ok' if self.succeeded else 'failed'})"
