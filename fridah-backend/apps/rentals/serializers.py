from rest_framework import serializers
from .models import Lease, Invoice, MaintenanceRequest, MaintenanceImage, LeaseRenewal, UtilityAccount, UtilityMeterReading, RentalApplication, AmenityCharge, AmenityExemption


class LeaseSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.get_full_name', read_only=True)
    unit_number = serializers.CharField(source='unit.unit_number', read_only=True)
    property_name = serializers.CharField(source='unit.property.name', read_only=True)

    class Meta:
        model = Lease
        fields = [
            'id', 'tenant', 'tenant_name', 'unit', 'unit_number', 'property_name', 'landlord',
            'start_date', 'end_date', 'rent_amount', 'deposit_amount', 'deposit_paid',
            'rent_due_day', 'status', 'terminated_at', 'termination_reason',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'landlord', 'created_at', 'updated_at']


class LeaseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lease
        fields = ['id', 'tenant', 'unit', 'start_date', 'end_date', 'rent_amount', 'deposit_amount', 'rent_due_day']
        read_only_fields = ['id']

    def create(self, validated_data):
        unit = validated_data['unit']
        validated_data['landlord'] = unit.property.landlord
        validated_data['status'] = Lease.Status.PENDING
        lease = super().create(validated_data)
        return lease


class RentalApplicationSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.get_full_name', read_only=True)
    unit_number = serializers.CharField(source='unit.unit_number', read_only=True)
    property_name = serializers.CharField(source='unit.property.name', read_only=True)
    rent_amount = serializers.DecimalField(source='unit.rent_amount', max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = RentalApplication
        fields = [
            'id', 'unit', 'unit_number', 'property_name', 'rent_amount', 'tenant', 'tenant_name',
            'message', 'preferred_move_in_date', 'status', 'resulting_lease', 'rejection_reason',
            'reviewed_by', 'reviewed_at', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'tenant', 'status', 'resulting_lease', 'rejection_reason',
            'reviewed_by', 'reviewed_at', 'created_at', 'updated_at',
        ]


class InvoiceSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.get_full_name', read_only=True)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    amenity_name = serializers.CharField(source='amenity_charge.name', read_only=True, default=None)

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'lease', 'tenant', 'tenant_name', 'invoice_type',
            'amount', 'amount_paid', 'balance', 'period_start', 'period_end', 'due_date',
            'status', 'is_overdue', 'pdf_receipt', 'created_at',
            'amenity_charge', 'amenity_name', 'waived_at', 'waiver_reason',
        ]
        read_only_fields = ['id', 'invoice_number', 'amount_paid', 'created_at']


class MaintenanceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceImage
        fields = ['id', 'image']


class MaintenanceRequestSerializer(serializers.ModelSerializer):
    images = MaintenanceImageSerializer(many=True, read_only=True)
    tenant_name = serializers.CharField(source='tenant.get_full_name', read_only=True)
    unit_number = serializers.CharField(source='unit.unit_number', read_only=True)
    property_name = serializers.CharField(source='unit.property.name', read_only=True)
    provider_name = serializers.CharField(source='assigned_provider.get_full_name', read_only=True)

    class Meta:
        model = MaintenanceRequest
        fields = [
            'id', 'tenant', 'tenant_name', 'unit', 'unit_number', 'property_name', 'category',
            'title', 'description', 'priority', 'status', 'assigned_provider', 'provider_name',
            'resolved_at', 'resolution_notes', 'images', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'tenant', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['tenant'] = self.context['request'].user
        return super().create(validated_data)


class LeaseRenewalSerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='lease.tenant.get_full_name', read_only=True)
    unit_number = serializers.CharField(source='lease.unit.unit_number', read_only=True)
    property_name = serializers.CharField(source='lease.unit.property.name', read_only=True)
    current_rent_amount = serializers.DecimalField(source='lease.rent_amount', max_digits=12, decimal_places=2, read_only=True)
    current_end_date = serializers.DateField(source='lease.end_date', read_only=True)

    class Meta:
        model = LeaseRenewal
        fields = [
            'id', 'lease', 'tenant_name', 'unit_number', 'property_name',
            'current_rent_amount', 'current_end_date',
            'proposed_start_date', 'proposed_end_date', 'proposed_rent_amount',
            'status', 'notified_60_day_at', 'notified_30_day_at', 'responded_at',
            'decline_reason', 'renewed_lease', 'created_at',
        ]
        read_only_fields = [
            'id', 'lease', 'status', 'notified_60_day_at', 'notified_30_day_at',
            'responded_at', 'renewed_lease', 'created_at',
        ]


class LeaseRenewalOfferUpdateSerializer(serializers.ModelSerializer):
    """Landlord adjusts the proposed terms (e.g. applying an annual rent escalation) before the tenant sees it."""
    class Meta:
        model = LeaseRenewal
        fields = ['proposed_start_date', 'proposed_end_date', 'proposed_rent_amount']

    def validate(self, attrs):
        if self.instance.status != LeaseRenewal.Status.PENDING:
            raise serializers.ValidationError("Only pending renewal offers can be edited.")
        return attrs


class LeaseRenewalRespondSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    decline_reason = serializers.CharField(required=False, allow_blank=True, default='')


class UtilityAccountSerializer(serializers.ModelSerializer):
    unit_number = serializers.CharField(source='unit.unit_number', read_only=True)
    property_name = serializers.CharField(source='unit.property.name', read_only=True)

    class Meta:
        model = UtilityAccount
        fields = [
            'id', 'unit', 'unit_number', 'property_name', 'utility_type', 'provider_name',
            'account_number', 'is_metered', 'rate_per_unit', 'flat_monthly_fee', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class UtilityMeterReadingSerializer(serializers.ModelSerializer):
    utility_type = serializers.CharField(source='utility_account.utility_type', read_only=True)
    generated_invoice_id = serializers.UUIDField(source='generated_invoice.id', read_only=True)
    generated_invoice_amount = serializers.DecimalField(source='generated_invoice.amount', max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = UtilityMeterReading
        fields = [
            'id', 'utility_account', 'utility_type', 'reading_value', 'reading_date', 'photo',
            'recorded_by', 'generated_invoice_id', 'generated_invoice_amount', 'created_at',
        ]
        read_only_fields = ['id', 'recorded_by', 'generated_invoice_id', 'generated_invoice_amount', 'created_at']


class AmenityChargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmenityCharge
        fields = ['id', 'property', 'name', 'description', 'amount', 'frequency',
                  'applies_to_all_units', 'units', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than zero.')
        return value

    def validate(self, attrs):
        prop = attrs.get('property') or getattr(self.instance, 'property', None)
        units = attrs.get('units')
        if units and any(u.property_id != prop.id for u in units):
            raise serializers.ValidationError({'units': 'All units must belong to the charge\'s property.'})
        return attrs


class AmenityExemptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmenityExemption
        fields = ['id', 'charge', 'lease', 'reason', 'created_at']
        read_only_fields = ['id', 'created_at']
