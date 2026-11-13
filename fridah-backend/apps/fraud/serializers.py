from rest_framework import serializers
from .models import FraudFlag


class FraudFlagSerializer(serializers.ModelSerializer):
    reviewed_by_name = serializers.CharField(source='reviewed_by.get_full_name', read_only=True)

    class Meta:
        model = FraudFlag
        fields = [
            'id', 'flag_type', 'status', 'subject_type', 'subject_id', 'reason', 'evidence',
            'reviewed_by', 'reviewed_by_name', 'reviewed_at', 'review_notes', 'created_at',
        ]
        read_only_fields = [
            'id', 'flag_type', 'subject_type', 'subject_id', 'reason', 'evidence',
            'reviewed_by', 'reviewed_at', 'created_at',
        ]


class FraudFlagReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[FraudFlag.Status.CONFIRMED, FraudFlag.Status.DISMISSED, FraudFlag.Status.REVIEWING])
    review_notes = serializers.CharField(required=False, allow_blank=True, default='')
