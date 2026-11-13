import secrets
import uuid
from django.db import models
from django.conf import settings


class Visitor(models.Model):
    """
    A tenant pre-registers an expected visitor and gets a QR token (a random opaque
    string, not the row's UUID, so a leaked/observed pass can't be re-derived from a
    guessable ID). Security scans the QR to check the visitor in, then out.
    """
    class Status(models.TextChoices):
        PRE_REGISTERED = 'pre_registered', 'Pre-registered'
        CHECKED_IN = 'checked_in', 'Checked In'
        CHECKED_OUT = 'checked_out', 'Checked Out'
        EXPIRED = 'expired', 'Expired'
        CANCELLED = 'cancelled', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.ForeignKey('properties.Unit', on_delete=models.CASCADE, related_name='visitors')
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='visitors_registered'
    )

    visitor_name = models.CharField(max_length=150)
    visitor_phone = models.CharField(max_length=20, blank=True)
    visitor_id_number = models.CharField(max_length=30, blank=True)
    purpose = models.CharField(max_length=200, blank=True)

    qr_token = models.CharField(max_length=64, unique=True, editable=False)
    expected_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PRE_REGISTERED)

    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_in_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='visitor_checkins'
    )
    checked_out_at = models.DateTimeField(null=True, blank=True)
    checked_out_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='visitor_checkouts'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'visitors'
        indexes = [
            models.Index(fields=['qr_token']),
            models.Index(fields=['unit', 'expected_date']),
        ]

    def save(self, *args, **kwargs):
        if not self.qr_token:
            self.qr_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.visitor_name} -> {self.unit} ({self.status})"
