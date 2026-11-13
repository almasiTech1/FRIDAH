from rest_framework import serializers
from .models import Visitor


class VisitorSerializer(serializers.ModelSerializer):
    unit_number = serializers.CharField(source='unit.unit_number', read_only=True)
    property_name = serializers.CharField(source='unit.property.name', read_only=True)
    registered_by_name = serializers.CharField(source='registered_by.get_full_name', read_only=True)

    class Meta:
        model = Visitor
        fields = [
            'id', 'unit', 'unit_number', 'property_name', 'registered_by', 'registered_by_name',
            'visitor_name', 'visitor_phone', 'visitor_id_number', 'purpose', 'qr_token',
            'expected_date', 'status', 'checked_in_at', 'checked_out_at', 'created_at',
        ]
        read_only_fields = ['id', 'registered_by', 'qr_token', 'status', 'checked_in_at', 'checked_out_at', 'created_at']

    def create(self, validated_data):
        validated_data['registered_by'] = self.context['request'].user
        return super().create(validated_data)


class VisitorQRScanSerializer(serializers.Serializer):
    qr_token = serializers.CharField()
