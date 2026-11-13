import uuid
from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    """
    Platform-wide, append-only audit trail. Every financial action (payments,
    payouts, allocations, advances, provider settlements) and every permission
    change (roles, assignments, KYC decisions) should be recorded here so any
    property/person/transaction's history can be reconstructed. Complements
    apps.agencies.AgencyAuditLog, which is scoped specifically to one agency's
    internal staffing/finance actions; this log spans the whole platform.
    """
    class Severity(models.TextChoices):
        INFO = 'info', 'Info'
        WARNING = 'warning', 'Warning'
        CRITICAL = 'critical', 'Critical'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_actions'
    )
    action = models.CharField(max_length=120, db_index=True)  # e.g. 'payment.completed', 'invoice.reconciled'
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.INFO)

    target_type = models.CharField(max_length=100, blank=True)
    target_id = models.CharField(max_length=64, blank=True)

    property = models.ForeignKey(
        'properties.Property', on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs'
    )

    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['target_type', 'target_id']),
            models.Index(fields=['property', 'created_at']),
        ]

    def __str__(self):
        return f"{self.action} by {self.actor} @ {self.created_at:%Y-%m-%d %H:%M}"
