from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Property, PropertyImage, Unit, UnitImage, SavedProperty, PropertyReview, PropertyDocument, PropertyApproval,
)
from common.fields import LatitudeField, LongitudeField

User = get_user_model()


class PropertyImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyImage
        fields = ['id', 'image', 'caption', 'is_primary', 'order']


class UnitImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitImage
        fields = ['id', 'image', 'is_primary', 'order']


class UnitSerializer(serializers.ModelSerializer):
    images = UnitImageSerializer(many=True, read_only=True)
    property_name = serializers.CharField(source='property.name', read_only=True)

    class Meta:
        model = Unit
        fields = [
            'id', 'property', 'property_name', 'unit_number', 'bedrooms', 'bathrooms',
            'size_sqm', 'rent_amount', 'deposit_amount', 'status', 'floor', 'description',
            'images', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PropertyReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source='reviewer.get_full_name', read_only=True)

    class Meta:
        model = PropertyReview
        fields = ['id', 'property', 'reviewer', 'reviewer_name', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'reviewer', 'created_at']


class PropertyListSerializer(serializers.ModelSerializer):
    vacant_units_count = serializers.IntegerField(read_only=True)
    primary_image = serializers.SerializerMethodField()
    min_rent = serializers.SerializerMethodField()
    landlord_name = serializers.CharField(source='landlord.get_full_name', read_only=True)

    class Meta:
        model = Property
        fields = [
            'id', 'name', 'property_type', 'status', 'county', 'town', 'estate',
            'total_units', 'vacant_units_count', 'amenities', 'primary_image',
            'min_rent', 'landlord', 'landlord_name', 'latitude', 'longitude', 'created_at',
            'review_state', 'requires_landlord_approval',
        ]
        read_only_fields = ['status', 'review_state', 'requires_landlord_approval']

    def get_primary_image(self, obj):
        img = obj.images.filter(is_primary=True).first() or obj.images.first()
        return img.image.url if img else None

    def get_min_rent(self, obj):
        unit = obj.units.order_by('rent_amount').first()
        return unit.rent_amount if unit else None


class PropertyDetailSerializer(serializers.ModelSerializer):
    images = PropertyImageSerializer(many=True, read_only=True)
    units = UnitSerializer(many=True, read_only=True)
    reviews = PropertyReviewSerializer(many=True, read_only=True)
    vacant_units_count = serializers.IntegerField(read_only=True)
    landlord_name = serializers.CharField(source='landlord.get_full_name', read_only=True)
    landlord_phone = serializers.CharField(source='landlord.phone_number', read_only=True)
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            'id', 'landlord', 'landlord_name', 'landlord_phone', 'name', 'description',
            'property_type', 'status', 'county', 'town', 'estate', 'address_detail',
            'latitude', 'longitude', 'total_units', 'vacant_units_count', 'amenities',
            'caretaker_name', 'caretaker_phone', 'images', 'units', 'reviews',
            'average_rating', 'created_at', 'updated_at',
            'review_state', 'submission_version', 'requires_landlord_approval',
        ]
        # `status` and the approval fields are only ever changed by the approval workflow
        # (apps/properties/approvals.py). Leaving `status` writable let an owner or agency
        # publish their own listing with a PATCH and skip approval entirely.
        read_only_fields = [
            'id', 'landlord', 'status', 'created_at', 'updated_at',
            'review_state', 'submission_version', 'requires_landlord_approval',
        ]

    def get_average_rating(self, obj):
        reviews = obj.reviews.all()
        if not reviews:
            return None
        return round(sum(r.rating for r in reviews) / len(reviews), 1)


class PropertyCreateSerializer(serializers.ModelSerializer):
    latitude = LatitudeField()
    longitude = LongitudeField()
    landlord = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='landlord'), required=False,
    )

    class Meta:
        model = Property
        fields = [
            'id', 'name', 'description', 'property_type', 'county', 'town', 'estate',
            'address_detail', 'latitude', 'longitude', 'total_units', 'amenities',
            'caretaker_name', 'caretaker_phone', 'landlord',
        ]
        read_only_fields = ['id']

    def validate_landlord(self, value):
        requester = self.context['request'].user
        if requester.role == 'admin' or value == requester:
            return value
        # Agency staff routinely onboard a landlord client's property themselves
        # (data entry on the client's behalf) rather than requiring the landlord
        # to self-register and enter it - any active agency membership can do
        # this; which properties that staff member can subsequently *manage*
        # is still governed separately by PropertyStaffAssignment/agency
        # permissions once the property exists and is assigned to their agency.
        from apps.agencies.models import AgencyMembership
        has_agency_membership = AgencyMembership.objects.filter(
            user=requester, status=AgencyMembership.Status.ACTIVE,
        ).exists()
        if has_agency_membership:
            return value
        raise serializers.ValidationError(
            "Only an admin, agency staff, or the landlord themselves can create a property on behalf of another landlord."
        )

    def create(self, validated_data):
        from . import approvals
        requester = self.context['request'].user
        if requester.role == 'admin':
            # Admin must specify who the property actually belongs to - an admin
            # onboarding a property isn't themselves the landlord of it.
            if 'landlord' not in validated_data:
                raise serializers.ValidationError({'landlord': "Required when an admin creates a property."})
        else:
            # validate_landlord() above already enforced who may set this to someone other
            # than themselves (agency staff onboarding a client's property).
            validated_data.setdefault('landlord', requester)
        # Everything starts pending. approvals.submit() decides which approvals are required
        # (landlord + admin for agent-submitted, admin only otherwise) and publishes
        # admin-created properties immediately. Nothing is published from here.
        validated_data['status'] = Property.Status.PENDING_APPROVAL
        prop = super().create(validated_data)
        return approvals.submit(prop, requester)


class SavedPropertySerializer(serializers.ModelSerializer):
    property_detail = PropertyListSerializer(source='property', read_only=True)

    class Meta:
        model = SavedProperty
        fields = ['id', 'property', 'property_detail', 'created_at']
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class PropertyDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)

    class Meta:
        model = PropertyDocument
        fields = [
            'id', 'property', 'document_type', 'document_type_display', 'title', 'file',
            'version', 'is_current', 'expiry_date', 'notes',
            'uploaded_by', 'uploaded_by_name', 'created_at',
        ]
        read_only_fields = ['id', 'version', 'is_current', 'uploaded_by', 'created_at']

    def create(self, validated_data):
        from django.db import transaction
        validated_data['uploaded_by'] = self.context['request'].user

        with transaction.atomic():
            # New upload of the same document_type supersedes the previous version
            # rather than overwriting it, so history is preserved for audits/disputes.
            latest = (
                PropertyDocument.objects
                .select_for_update()
                .filter(property=validated_data['property'], document_type=validated_data['document_type'])
                .order_by('-version')
                .first()
            )
            validated_data['version'] = (latest.version + 1) if latest else 1
            if latest:
                latest.is_current = False
                latest.save(update_fields=['is_current'])
            return super().create(validated_data)


class PropertyApprovalSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.get_full_name', read_only=True, default=None)

    class Meta:
        model = PropertyApproval
        fields = [
            'id', 'property', 'party', 'decision', 'submission_version', 'actor', 'actor_name',
            'comment', 'from_state', 'to_state', 'created_at',
        ]
        read_only_fields = fields
