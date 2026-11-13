from rest_framework import serializers
from .models import (
    Agency, AgencyRole, AgencyMembership, PropertyManagementAssignment, PropertyStaffAssignment,
    AgencyFeeRule, ManagementAgreement, OwnerStatement, OwnerPayout, AgencyCommission,
    AgencyExpense, AgencyAuditLog,
)


class AgencySerializer(serializers.ModelSerializer):
    managed_properties_count = serializers.IntegerField(read_only=True)
    owners_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Agency
        fields = [
            'id', 'name', 'registration_number', 'kra_pin', 'status', 'logo', 'email',
            'phone_number', 'county', 'town', 'address_detail', 'default_fee_percent',
            'managed_properties_count', 'owners_count', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']


class AgencyRegistrationSerializer(AgencySerializer):
    """
    Admin-only. The agency's details plus the person who will be its first Agency Admin; the admin
    creates that person's login here (nobody self-registers an agency).
    """
    admin_first_name = serializers.CharField(write_only=True, max_length=150)
    admin_last_name = serializers.CharField(write_only=True, max_length=150)
    admin_email = serializers.EmailField(write_only=True)
    admin_phone_number = serializers.CharField(write_only=True, max_length=13)
    agency_admin = serializers.SerializerMethodField()

    class Meta(AgencySerializer.Meta):
        fields = AgencySerializer.Meta.fields + [
            'admin_first_name', 'admin_last_name', 'admin_email', 'admin_phone_number', 'agency_admin',
        ]

    def get_agency_admin(self, obj):
        m = obj.memberships.filter(role__role_type='agency_admin').select_related('user').first()
        return {'id': str(m.user_id), 'name': m.user.get_full_name(), 'email': m.user.email} if m else None

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Agency name is required.')
        return value

    def validate_admin_email(self, value):
        from apps.users.models import User
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists. Use a different email for the agency admin.')
        return value

    def validate_admin_phone_number(self, value):
        from apps.users.models import User
        from django.core.exceptions import ValidationError as DjangoValidationError
        field = User._meta.get_field('phone_number')
        try:
            for v in field.validators:
                v(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError('An account with this phone number already exists.')
        return value


class AgencyDirectorySerializer(serializers.ModelSerializer):
    """
    Deliberately limited fields for the public-within-platform directory search - just
    enough for a property owner to identify and pick an agency to work with. Excludes
    fee rules, staff, and anything else that's only appropriate for the agency's own
    staff or an owner who has already engaged them.
    """
    managed_properties_count = serializers.IntegerField(read_only=True)
    owners_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Agency
        fields = ['id', 'name', 'logo', 'county', 'town', 'managed_properties_count', 'owners_count']
        read_only_fields = fields


class AgencyRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgencyRole
        fields = ['id', 'agency', 'name', 'role_type', 'permissions', 'created_at']
        read_only_fields = ['id', 'created_at']


class AgencyMembershipSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)
    role_type = serializers.CharField(source='role.role_type', read_only=True)

    class Meta:
        model = AgencyMembership
        fields = [
            'id', 'agency', 'user', 'user_name', 'user_email', 'role', 'role_name', 'role_type',
            'status', 'invited_by', 'joined_at', 'removed_at', 'created_at',
        ]
        read_only_fields = ['id', 'status', 'invited_by', 'joined_at', 'removed_at', 'created_at']


class InviteStaffSerializer(serializers.Serializer):
    """
    Add a staff member. If the email already belongs to a FRIDAH account they are invited; otherwise the
    agency creates their login, which needs first_name, last_name and phone_number.
    """
    email = serializers.EmailField()
    role_id = serializers.UUIDField()
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    phone_number = serializers.CharField(required=False, allow_blank=True, max_length=13)


class PropertyStaffAssignmentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='membership.user.get_full_name', read_only=True)
    property_name = serializers.CharField(source='property.name', read_only=True)

    class Meta:
        model = PropertyStaffAssignment
        fields = ['id', 'property', 'property_name', 'membership', 'user_name', 'is_active', 'assigned_at', 'removed_at']
        read_only_fields = ['id', 'assigned_at', 'removed_at']


class AgencyFeeRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgencyFeeRule
        fields = ['id', 'agency', 'name', 'fee_type', 'fee_value', 'is_default', 'created_at']
        read_only_fields = ['id', 'created_at']


class ManagementAgreementSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source='property.name', read_only=True)
    agency_name = serializers.CharField(source='agency.name', read_only=True)
    is_fully_signed = serializers.BooleanField(read_only=True)

    class Meta:
        model = ManagementAgreement
        fields = [
            'id', 'property', 'property_name', 'agency', 'agency_name', 'owner', 'fee_rule',
            'management_fee_percent', 'payout_rule', 'start_date', 'end_date', 'status',
            'document', 'terms', 'signed_by_owner_at', 'signed_by_agency_at', 'is_fully_signed',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'owner', 'status', 'signed_by_owner_at', 'signed_by_agency_at', 'created_at', 'updated_at',
        ]


class PropertyManagementAssignmentSerializer(serializers.ModelSerializer):
    property_name = serializers.SerializerMethodField()
    listing_name = serializers.SerializerMethodField()
    agency_name = serializers.CharField(source='agency.name', read_only=True)
    owner_name = serializers.SerializerMethodField()
    owner_email = serializers.SerializerMethodField()
    owner_phone = serializers.SerializerMethodField()
    item_type = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()

    class Meta:
        model = PropertyManagementAssignment
        fields = [
            'id', 'property', 'property_name', 'listing', 'listing_name', 'owner_name',
            'owner_email', 'owner_phone', 'item_type', 'location',
            'agency', 'agency_name', 'agreement', 'fee_rule', 'management_fee_percent',
            'payout_rule', 'start_date', 'end_date',
            'status', 'approved_by', 'ended_reason', 'ended_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'status', 'approved_by', 'ended_reason', 'ended_at', 'created_at', 'updated_at']

    def get_property_name(self, obj):
        return obj.property.name if obj.property_id else None

    def get_listing_name(self, obj):
        return obj.listing.name if obj.listing_id else None

    def _owner(self, obj):
        return obj.property.landlord if obj.property_id else (obj.listing.host if obj.listing_id else None)

    def get_owner_name(self, obj):
        owner = self._owner(obj)
        return (owner.get_full_name() or owner.email) if owner else None

    def get_owner_email(self, obj):
        owner = self._owner(obj)
        return owner.email if owner else None

    def get_owner_phone(self, obj):
        owner = self._owner(obj)
        return owner.phone_number if owner else None

    def get_item_type(self, obj):
        return 'property' if obj.property_id else 'listing'

    def get_location(self, obj):
        item = obj.property if obj.property_id else obj.listing
        return f"{item.town}, {item.county}" if item else ''


class AssignPropertySerializer(serializers.Serializer):
    property_id = serializers.UUIDField()
    agency_id = serializers.UUIDField()
    start_date = serializers.DateField()
    management_fee_percent = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    payout_rule = serializers.ChoiceField(choices=PropertyManagementAssignment.PayoutRule.choices, required=False)
    fee_rule_id = serializers.UUIDField(required=False, allow_null=True)


class AssignListingSerializer(serializers.Serializer):
    listing_id = serializers.UUIDField()
    agency_id = serializers.UUIDField()
    start_date = serializers.DateField()
    management_fee_percent = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    payout_rule = serializers.ChoiceField(choices=PropertyManagementAssignment.PayoutRule.choices, required=False)
    fee_rule_id = serializers.UUIDField(required=False, allow_null=True)


class OwnerStatementSerializer(serializers.ModelSerializer):
    property_name = serializers.SerializerMethodField()
    listing_name = serializers.SerializerMethodField()
    agency_name = serializers.CharField(source='agency.name', read_only=True, default=None)
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)

    class Meta:
        model = OwnerStatement
        fields = [
            'id', 'property', 'property_name', 'listing', 'listing_name', 'agency', 'agency_name', 'owner', 'owner_name',
            'period_start', 'period_end', 'gross_rent_collected', 'vacancy_loss', 'arrears',
            'agency_commission', 'approved_expenses', 'other_deductions', 'net_payable',
            'status', 'pdf_statement', 'issued_at', 'created_at',
        ]
        read_only_fields = [f for f in [
            'id', 'gross_rent_collected', 'vacancy_loss', 'arrears', 'agency_commission',
            'approved_expenses', 'net_payable', 'status', 'issued_at', 'created_at',
        ]]

    def get_property_name(self, obj):
        return obj.property.name if obj.property_id else None

    def get_listing_name(self, obj):
        return obj.listing.name if obj.listing_id else None


class GenerateStatementSerializer(serializers.Serializer):
    property_id = serializers.UUIDField()
    period_start = serializers.DateField()
    period_end = serializers.DateField()


class GenerateListingStatementSerializer(serializers.Serializer):
    listing_id = serializers.UUIDField()
    period_start = serializers.DateField()
    period_end = serializers.DateField()


class OwnerPayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = OwnerPayout
        fields = [
            'id', 'statement', 'owner', 'amount', 'method', 'phone_number', 'status',
            'reference', 'transaction_id', 'created_at', 'completed_at',
        ]
        read_only_fields = ['id', 'reference', 'transaction_id', 'status', 'created_at', 'completed_at']


class AgencyCommissionSerializer(serializers.ModelSerializer):
    property_name = serializers.SerializerMethodField()
    listing_name = serializers.SerializerMethodField()

    class Meta:
        model = AgencyCommission
        fields = [
            'id', 'agency', 'property', 'property_name', 'listing', 'listing_name', 'assignment', 'statement',
            'period_start', 'period_end', 'gross_amount', 'commission_rate', 'commission_amount', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_property_name(self, obj):
        return obj.property.name if obj.property_id else None

    def get_listing_name(self, obj):
        return obj.listing.name if obj.listing_id else None


class AgencyExpenseSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source='property.name', read_only=True)

    class Meta:
        model = AgencyExpense
        fields = [
            'id', 'agency', 'property', 'property_name', 'category', 'description', 'amount',
            'receipt', 'is_deductible_from_owner', 'incurred_on', 'recorded_by', 'approved_by',
            'statement', 'created_at',
        ]
        read_only_fields = ['id', 'recorded_by', 'statement', 'created_at']


class AgencyAuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.get_full_name', read_only=True, default=None)

    class Meta:
        model = AgencyAuditLog
        fields = ['id', 'agency', 'actor', 'actor_name', 'action', 'target_type', 'target_id', 'changes', 'created_at']
        read_only_fields = fields
