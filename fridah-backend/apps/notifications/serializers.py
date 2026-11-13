from rest_framework import serializers
from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'notification_type', 'is_read', 'metadata', 'created_at']
        read_only_fields = fields


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ['sms_enabled', 'email_enabled', 'push_enabled', 'payment_alerts', 'maintenance_alerts', 'marketing_alerts',
                  'quiet_hours_start', 'quiet_hours_end']
