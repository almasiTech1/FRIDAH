from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, OTP, TenantBlacklistEntry


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone_number', 'password', 'password_confirm',
            'first_name', 'last_name', 'role', 'county', 'town',
            'business_name', 'service_category',
        ]
        read_only_fields = ['id']

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({'password_confirm': "Passwords do not match."})
        if attrs.get('role') == User.Role.SERVICE_PROVIDER and not attrs.get('service_category'):
            raise serializers.ValidationError({'service_category': "Required for service providers."})
        # Security: 'role' was previously fully attacker-controlled, letting anyone register
        # with role="admin" directly through the public signup endpoint. Admin accounts must
        # be created via createsuperuser/seed_demo_users or promoted by an existing admin,
        # never through self-registration.
        allowed_self_registration_roles = {
            User.Role.TENANT, User.Role.LANDLORD, User.Role.SERVICE_PROVIDER, User.Role.HOTEL_OWNER,
        }
        if attrs.get('role') not in allowed_self_registration_roles:
            raise serializers.ValidationError({'role': "Invalid role for self-registration."})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.is_active = True
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs['email'], password=attrs['password'])
        if not user:
            # USERNAME_FIELD is email, but authenticate() checks username kwarg by default;
            # ModelBackend honors USERNAME_FIELD so this works against email.
            raise serializers.ValidationError("Invalid credentials.")
        if not user.is_active_account:
            raise serializers.ValidationError("Account has been deactivated. Contact support.")
        attrs['user'] = user
        return attrs


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()

    @staticmethod
    def for_user(user):
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['email'] = user.email
        return {'access': str(refresh.access_token), 'refresh': str(refresh)}


class UserSerializer(serializers.ModelSerializer):
    is_kyc_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone_number', 'first_name', 'last_name',
            'role', 'kyc_status', 'is_kyc_verified', 'is_phone_verified', 'is_email_verified',
            'county', 'town', 'profile_photo', 'business_name', 'service_category',
            'created_at', 'must_change_password',
        ]
        read_only_fields = ['id', 'kyc_status', 'is_phone_verified', 'is_email_verified', 'created_at', 'role',
                            'must_change_password']


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'county', 'town', 'profile_photo',
            'business_name', 'service_category', 'fcm_token',
        ]


class KYCSubmitSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['national_id', 'kyc_document']

    def validate_kyc_document(self, value):
        max_bytes = 5 * 1024 * 1024
        if value.size > max_bytes:
            raise serializers.ValidationError("Document must be under 5MB.")
        return value

    def update(self, instance, validated_data):
        instance.national_id = validated_data.get('national_id', instance.national_id)
        instance.kyc_document = validated_data.get('kyc_document', instance.kyc_document)
        instance.kyc_status = User.KYCStatus.PENDING
        instance.kyc_rejection_reason = None
        instance.save()
        return instance


class KYCReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)


class OTPRequestSerializer(serializers.Serializer):
    purpose = serializers.ChoiceField(choices=OTP.Purpose.choices)


class OTPVerifySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6, min_length=6)
    purpose = serializers.ChoiceField(choices=OTP.Purpose.choices)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs['new_password'] == attrs['old_password']:
            raise serializers.ValidationError({'new_password': "Choose a password different from the current one."})
        return attrs


class TenantBlacklistEntrySerializer(serializers.ModelSerializer):
    tenant_name = serializers.CharField(source='tenant.get_full_name', read_only=True)
    tenant_phone = serializers.CharField(source='tenant.phone_number', read_only=True)
    flagged_by_name = serializers.CharField(source='flagged_by.get_full_name', read_only=True)

    class Meta:
        model = TenantBlacklistEntry
        fields = [
            'id', 'tenant', 'tenant_name', 'tenant_phone', 'flagged_by', 'flagged_by_name',
            'lease', 'reason', 'details', 'amount_owed', 'status',
            'tenant_response', 'tenant_responded_at',
            'reviewed_by', 'reviewed_at', 'review_notes', 'created_at',
        ]
        read_only_fields = [
            'id', 'flagged_by', 'status', 'tenant_response', 'tenant_responded_at',
            'reviewed_by', 'reviewed_at', 'review_notes', 'created_at',
        ]

    def create(self, validated_data):
        validated_data['flagged_by'] = self.context['request'].user
        return super().create(validated_data)


class BlacklistTenantResponseSerializer(serializers.Serializer):
    response = serializers.CharField()


class BlacklistReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[TenantBlacklistEntry.Status.ACTIVE, TenantBlacklistEntry.Status.REMOVED])
    review_notes = serializers.CharField(required=False, allow_blank=True, default='')
