from rest_framework import serializers
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.get_full_name', read_only=True, default=None)
    property_name = serializers.CharField(source='property.name', read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = [
            'id', 'actor', 'actor_name', 'action', 'severity', 'target_type', 'target_id',
            'property', 'property_name', 'changes', 'ip_address', 'created_at',
        ]
        read_only_fields = fields
