from rest_framework import serializers

from .models import TaxType, TaxRule, TaxRecord, TaxAdjustment
from .services import ESTIMATE_LABEL


class TaxTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxType
        fields = ['id', 'code', 'name', 'description', 'is_active']
        read_only_fields = ['id']


class TaxRuleSerializer(serializers.ModelSerializer):
    tax_type_code = serializers.CharField(source='tax_type.code', read_only=True)
    is_professionally_reviewed = serializers.BooleanField(read_only=True)

    class Meta:
        model = TaxRule
        fields = [
            'id', 'tax_type', 'tax_type_code', 'version', 'method', 'rate', 'flat_amount', 'annual_threshold',
            'taxpayer_type', 'effective_from', 'effective_to', 'is_active', 'professional_reviewed_by',
            'professional_reviewed_on', 'is_professionally_reviewed', 'source_reference', 'notes', 'created_at',
        ]
        read_only_fields = ['id', 'version', 'created_at']
        # (tax_type, version) uniqueness is guaranteed by the view, which assigns the next
        # version number; DRF's auto validator would wrongly check the model default (1).
        validators = []

    def validate(self, attrs):
        start, end = attrs.get('effective_from'), attrs.get('effective_to')
        if start and end and end < start:
            raise serializers.ValidationError('effective_to cannot be before effective_from.')
        return attrs


class TaxAdjustmentSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.get_full_name', read_only=True, default=None)

    class Meta:
        model = TaxAdjustment
        fields = ['id', 'actor', 'actor_name', 'reason', 'before', 'after', 'created_at']


class TaxRecordSerializer(serializers.ModelSerializer):
    tax_type_code = serializers.CharField(source='tax_type.code', read_only=True)
    tax_type_name = serializers.CharField(source='tax_type.name', read_only=True)
    property_name = serializers.CharField(source='property.name', read_only=True, default=None)
    is_estimate = serializers.BooleanField(read_only=True)
    balance_due = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    label = serializers.SerializerMethodField()
    rule_version = serializers.IntegerField(source='rule.version', read_only=True, default=None)

    class Meta:
        model = TaxRecord
        fields = [
            'id', 'owner', 'property', 'property_name', 'tax_type', 'tax_type_code', 'tax_type_name',
            'rule_version', 'statement', 'period_start', 'period_end', 'gross_income', 'allowable_expenses',
            'withholding_credit', 'taxable_base', 'calculated_amount', 'amount_paid', 'balance_due', 'status',
            'is_estimate', 'label', 'reference', 'calculation_breakdown', 'updated_at',
        ]
        read_only_fields = fields

    def get_label(self, obj):
        return ESTIMATE_LABEL if obj.is_estimate else None
