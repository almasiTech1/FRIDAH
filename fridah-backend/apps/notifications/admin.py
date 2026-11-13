from django.contrib import admin
from .models import Notification, NotificationPreference, NotificationDelivery, RentReminderLog


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')


admin.site.register(NotificationPreference)
admin.site.register(NotificationDelivery)
admin.site.register(RentReminderLog)

from .messaging_models import (
    MessageThread, MessageParticipant, Message, MessageAttachment, MessageReaction,
    MessageDeliveryStatus, SharedObject, CallLog, Announcement,
)


@admin.register(MessageThread)
class MessageThreadAdmin(admin.ModelAdmin):
    list_display = ('id', 'thread_type', 'subject', 'is_group', 'updated_at')
    list_filter = ('thread_type', 'is_group')


admin.site.register(MessageParticipant)
admin.site.register(Message)
admin.site.register(MessageAttachment)
admin.site.register(MessageReaction)
admin.site.register(MessageDeliveryStatus)
admin.site.register(SharedObject)
admin.site.register(CallLog)


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('property', 'title', 'posted_by', 'created_at')
