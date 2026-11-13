import uuid
from django.db import models
from django.conf import settings


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        PAYMENT = 'payment', 'Payment'
        LEASE = 'lease', 'Lease'
        MAINTENANCE = 'maintenance', 'Maintenance'
        BOOKING = 'booking', 'Booking'
        JOB = 'job', 'Service Job'
        KYC = 'kyc', 'KYC'
        GENERAL = 'general', 'General'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=150)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices, default=NotificationType.GENERAL)
    is_read = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'is_read'])]


class NotificationDelivery(models.Model):
    """
    Per-channel dispatch record for a Notification (in_app/sms/email/push), so the
    rent-reminder engine and any other multi-channel notification can track exactly
    what was sent, through which channel, and whether it succeeded — independent of
    whether the in-app Notification itself was read.
    """
    class Channel(models.TextChoices):
        IN_APP = 'in_app', 'In-App'
        SMS = 'sms', 'SMS'
        EMAIL = 'email', 'Email'
        PUSH = 'push', 'Push'
        WHATSAPP = 'whatsapp', 'WhatsApp'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT = 'sent', 'Sent'
        FAILED = 'failed', 'Failed'
        SKIPPED = 'skipped', 'Skipped (preference disabled)'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='deliveries')
    channel = models.CharField(max_length=10, choices=Channel.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    provider_reference = models.CharField(max_length=100, blank=True)
    error_message = models.CharField(max_length=255, blank=True)
    attempts = models.PositiveSmallIntegerField(default=1)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notification_deliveries'
        indexes = [models.Index(fields=['channel', 'status'])]

    def __str__(self):
        return f"{self.notification_id} via {self.channel} ({self.status})"


class RentReminderLog(models.Model):
    """
    De-duplication record so the rent-reminder engine sends each (invoice, trigger)
    combination — e.g. '3 days before due', 'due today', 'overdue day 1' — only once.
    """
    class Trigger(models.TextChoices):
        DUE_IN_7_DAYS = 'due_in_7', 'Due in 7 Days'
        DUE_IN_3_DAYS = 'due_in_3', 'Due in 3 Days'
        DUE_IN_1_DAY = 'due_in_1', 'Due in 1 Day'
        DUE_TODAY = 'due_today', 'Due Today'
        OVERDUE = 'overdue', 'Overdue'
        PAYMENT_RECEIVED = 'payment_received', 'Payment Received'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey('rentals.Invoice', on_delete=models.CASCADE, related_name='reminder_logs')
    trigger = models.CharField(max_length=20, choices=Trigger.choices)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'rent_reminder_logs'
        unique_together = ('invoice', 'trigger')


class NotificationPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preferences')
    sms_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)
    payment_alerts = models.BooleanField(default=True)
    maintenance_alerts = models.BooleanField(default=True)
    marketing_alerts = models.BooleanField(default=False)
    # Quiet hours (Africa/Nairobi local time). While active, reminders are held back and sent
    # once the window ends. Null = use the platform default (settings.NOTIFICATION_DEFAULT_QUIET_HOURS).
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)

    class Meta:
        db_table = 'notification_preferences'
