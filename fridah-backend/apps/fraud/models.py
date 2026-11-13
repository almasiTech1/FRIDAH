import uuid
from django.db import models


class FraudFlag(models.Model):
    """
    A rule-based fraud signal surfaced for admin review. Detection is deliberately
    conservative and explainable (no black-box scoring) - these are flags to
    investigate, not automatic account actions.
    """
    class FlagType(models.TextChoices):
        DUPLICATE_LISTING = 'duplicate_listing', 'Duplicate Listing'
        SUSPICIOUS_PAYMENT_PATTERN = 'suspicious_payment_pattern', 'Suspicious Payment Pattern'
        ABNORMAL_PRICING = 'abnormal_pricing', 'Abnormal Pricing'
        MULTI_ACCOUNT_PHONE = 'multi_account_phone', 'Multiple Accounts, Same Phone'

    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        REVIEWING = 'reviewing', 'Under Review'
        CONFIRMED = 'confirmed', 'Confirmed Fraud'
        DISMISSED = 'dismissed', 'Dismissed (False Positive)'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    flag_type = models.CharField(max_length=40, choices=FlagType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)

    # Generic-ish reference rather than a hard FK to any one model, since flags can point
    # at a Property, a User, or a Payment depending on flag_type.
    subject_type = models.CharField(max_length=30)  # 'property', 'user', 'payment'
    subject_id = models.CharField(max_length=64)

    reason = models.TextField()
    evidence = models.JSONField(default=dict, blank=True)  # e.g. matched property IDs, phone numbers, counts

    reviewed_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='fraud_flags_reviewed'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'fraud_flags'
        indexes = [
            models.Index(fields=['flag_type', 'status']),
            models.Index(fields=['subject_type', 'subject_id']),
        ]

    def __str__(self):
        return f"{self.get_flag_type_display()} - {self.subject_type}:{self.subject_id} ({self.status})"
