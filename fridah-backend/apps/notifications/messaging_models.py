import uuid
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class MessageThread(models.Model):
    """
    A FRIDAH Chat conversation. Originally a simple tenant<->landlord thread tied to a
    lease; extended (not replaced) with a thread_type so the same model can represent
    every relationship-based conversation the platform needs: tenant<->landlord,
    tenant<->agency, tenant<->caretaker, tenant<->service-provider, landlord<->agency,
    agency<->service-provider, property groups, listing inquiries and maintenance/service
    job chats.
    """
    class ThreadType(models.TextChoices):
        TENANT_LANDLORD = 'tenant_landlord', 'Tenant ↔ Landlord'
        TENANT_AGENCY = 'tenant_agency', 'Tenant ↔ Agency'
        TENANT_CARETAKER = 'tenant_caretaker', 'Tenant ↔ Caretaker'
        TENANT_PROVIDER = 'tenant_provider', 'Tenant ↔ Service Provider'
        LANDLORD_AGENCY = 'landlord_agency', 'Landlord ↔ Agency'
        AGENCY_PROVIDER = 'agency_provider', 'Agency ↔ Service Provider'
        PROPERTY_GROUP = 'property_group', 'Property Group'
        LISTING_INQUIRY = 'listing_inquiry', 'Listing Inquiry'
        HOTEL_GUEST = 'hotel_guest', 'Hotel/BnB Host ↔ Guest'
        SERVICE_JOB = 'service_job', 'Maintenance / Service Job'
        DIRECT = 'direct', 'Direct Message'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread_type = models.CharField(max_length=20, choices=ThreadType.choices, default=ThreadType.DIRECT)

    # Relationship anchors — a thread should be justified by at least one of these,
    # not merely by who was added as a participant.
    lease = models.ForeignKey('rentals.Lease', on_delete=models.CASCADE, related_name='message_threads', null=True, blank=True)
    property = models.ForeignKey('properties.Property', on_delete=models.CASCADE, related_name='message_threads', null=True, blank=True)
    service_job = models.ForeignKey('services.ServiceJob', on_delete=models.CASCADE, related_name='message_threads', null=True, blank=True)
    maintenance_request = models.ForeignKey(
        'rentals.MaintenanceRequest', on_delete=models.CASCADE, related_name='message_threads', null=True, blank=True
    )
    listing = models.ForeignKey('bookings.Listing', on_delete=models.CASCADE, related_name='message_threads', null=True, blank=True)
    agency = models.ForeignKey('agencies.Agency', on_delete=models.SET_NULL, related_name='message_threads', null=True, blank=True)

    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name='message_threads', through='MessageParticipant'
    )
    is_group = models.BooleanField(default=False)
    subject = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='threads_created'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'message_threads'
        ordering = ['-updated_at']
        indexes = [models.Index(fields=['thread_type']), models.Index(fields=['property'])]

    def __str__(self):
        return self.subject or f"{self.get_thread_type_display()} ({self.id})"

    def unread_count_for(self, user):
        try:
            participant = self.thread_participants.get(user=user)
        except MessageParticipant.DoesNotExist:
            return 0
        qs = self.messages.exclude(sender=user)
        if participant.last_read_at:
            qs = qs.filter(created_at__gt=participant.last_read_at)
        return qs.count()

    def mark_read_for(self, user):
        from django.utils import timezone
        MessageParticipant.objects.filter(thread=self, user=user).update(last_read_at=timezone.now())
        MessageDeliveryStatus.objects.filter(
            message__thread=self, user=user, status=MessageDeliveryStatus.Status.DELIVERED
        ).update(status=MessageDeliveryStatus.Status.READ, read_at=timezone.now())


class MessageParticipant(models.Model):
    """Through-model for thread membership: per-user read cursor, mute/admin flags, join/leave history."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey(MessageThread, on_delete=models.CASCADE, related_name='thread_participants')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='thread_memberships')
    is_admin = models.BooleanField(default=False)  # can manage group participants
    is_muted = models.BooleanField(default=False)
    last_read_at = models.DateTimeField(null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'message_participants'
        unique_together = ('thread', 'user')

    def __str__(self):
        return f"{self.user} in {self.thread_id}"


class SharedObject(models.Model):
    """
    A rich share card referencing an existing platform object (property, invoice,
    payment, maintenance request, booking, document, lease) so it can be shown inline
    in chat instead of a plain link. `card_data` is a denormalized snapshot (title,
    image, price, status at share time) so the card renders instantly without a
    follow-up fetch; `content_object` is the live link for "View" / "Pay Now" actions.
    """
    class ObjectType(models.TextChoices):
        PROPERTY = 'property', 'Property'
        UNIT = 'unit', 'Unit'
        INVOICE = 'invoice', 'Invoice'
        PAYMENT = 'payment', 'Payment'
        MAINTENANCE_REQUEST = 'maintenance_request', 'Maintenance Request'
        SERVICE_JOB = 'service_job', 'Service Job'
        BOOKING = 'booking', 'Booking'
        LEASE = 'lease', 'Lease'
        DOCUMENT = 'document', 'Document'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    object_type = models.CharField(max_length=30, choices=ObjectType.choices)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.UUIDField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    card_data = models.JSONField(default=dict, blank=True)
    shared_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='shared_objects')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'shared_objects'
        indexes = [models.Index(fields=['object_type']), models.Index(fields=['content_type', 'object_id'])]

    def __str__(self):
        return f"{self.get_object_type_display()} shared by {self.shared_by}"


class Message(models.Model):
    class MessageType(models.TextChoices):
        TEXT = 'text', 'Text'
        IMAGE = 'image', 'Image'
        VIDEO = 'video', 'Video'
        DOCUMENT = 'document', 'Document'
        VOICE_NOTE = 'voice_note', 'Voice Note'
        PROPERTY_CARD = 'property_card', 'Property Card'
        INVOICE_CARD = 'invoice_card', 'Invoice Card'
        PAYMENT_REQUEST = 'payment_request', 'Payment Request'
        MAINTENANCE_CARD = 'maintenance_card', 'Maintenance Card'
        BOOKING_CARD = 'booking_card', 'Booking Card'
        LEASE_CARD = 'lease_card', 'Lease / Document Card'
        SYSTEM = 'system', 'System Message'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey(MessageThread, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_messages'
    )
    message_type = models.CharField(max_length=20, choices=MessageType.choices, default=MessageType.TEXT)
    body = models.TextField(blank=True)

    shared_object = models.ForeignKey(SharedObject, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')
    reply_to = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')

    # Original single-file field, kept for backward compatibility with existing rows/clients.
    # New uploads should use MessageAttachment (supports multiple files + voice-note metadata).
    attachment = models.FileField(upload_to='message_attachments/', blank=True, null=True)

    is_read = models.BooleanField(default=False)  # legacy 1:1-thread flag, superseded by MessageDeliveryStatus for groups
    is_edited = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'messages'
        ordering = ['created_at']
        indexes = [models.Index(fields=['thread', 'created_at'])]

    def __str__(self):
        return f"{self.sender}: {self.body[:40]}"


class MessageAttachment(models.Model):
    class FileType(models.TextChoices):
        IMAGE = 'image', 'Image'
        VIDEO = 'video', 'Video'
        DOCUMENT = 'document', 'Document'
        VOICE_NOTE = 'voice_note', 'Voice Note'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='message_attachments/%Y/%m/')
    file_type = models.CharField(max_length=20, choices=FileType.choices)
    thumbnail = models.ImageField(upload_to='message_attachment_thumbs/%Y/%m/', blank=True, null=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)  # voice notes / video
    file_size_bytes = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'message_attachments'

    def __str__(self):
        return f"{self.get_file_type_display()} on message {self.message_id}"


class MessageReaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='message_reactions')
    emoji = models.CharField(max_length=8)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'message_reactions'
        unique_together = ('message', 'user', 'emoji')


class MessageDeliveryStatus(models.Model):
    """Per-recipient sent/delivered/read receipt (WhatsApp-style single/double/blue ticks), one row per participant."""
    class Status(models.TextChoices):
        SENT = 'sent', 'Sent'
        DELIVERED = 'delivered', 'Delivered'
        READ = 'read', 'Read'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='delivery_statuses')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='message_delivery_statuses')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SENT)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'message_delivery_statuses'
        unique_together = ('message', 'user')


class CallLog(models.Model):
    """
    Call button records. Phase 1 (current): dials out via the device's native phone
    dialler and simply logs the attempt/outcome. FRIDAH Voice/Video (in-app calling)
    is a later phase that can populate the same log with richer session data.
    """
    class CallType(models.TextChoices):
        VOICE = 'voice', 'Voice'
        VIDEO = 'video', 'Video'

    class Status(models.TextChoices):
        INITIATED = 'initiated', 'Initiated'
        RINGING = 'ringing', 'Ringing'
        ANSWERED = 'answered', 'Answered'
        MISSED = 'missed', 'Missed'
        REJECTED = 'rejected', 'Rejected'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey(MessageThread, on_delete=models.SET_NULL, null=True, blank=True, related_name='calls')
    caller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='calls_made')
    callee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='calls_received')

    call_type = models.CharField(max_length=10, choices=CallType.choices, default=CallType.VOICE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INITIATED)

    started_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'call_logs'
        ordering = ['-started_at']
        indexes = [models.Index(fields=['caller', 'callee'])]

    def __str__(self):
        return f"{self.get_call_type_display()} call {self.caller} -> {self.callee} ({self.status})"


class Announcement(models.Model):
    """Broadcast a notice to all active tenants of a property. Authorized by ownership OR agency management rights."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property = models.ForeignKey('properties.Property', on_delete=models.CASCADE, related_name='announcements')
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='announcements', null=True, blank=True
    )  # nullable only to allow a clean migration from the old `landlord` field; always set on create going forward
    agency = models.ForeignKey('agencies.Agency', on_delete=models.SET_NULL, null=True, blank=True, related_name='announcements')
    title = models.CharField(max_length=200)
    body = models.TextField()
    send_sms = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'announcements'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.property} - {self.title}"
