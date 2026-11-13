from rest_framework import serializers
from .models import ServiceCategory, ServiceJob, Quote, ServiceProviderProfile, JobReview


class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ['id', 'name', 'icon', 'description']


class QuoteSerializer(serializers.ModelSerializer):
    provider_name = serializers.CharField(source='provider.get_full_name', read_only=True)
    provider_phone = serializers.CharField(source='provider.phone_number', read_only=True)

    class Meta:
        model = Quote
        fields = ['id', 'job', 'provider', 'provider_name', 'provider_phone', 'amount', 'message', 'estimated_days', 'status', 'created_at']
        read_only_fields = ['id', 'provider', 'status', 'created_at']

    def create(self, validated_data):
        validated_data['provider'] = self.context['request'].user
        return super().create(validated_data)


class ServiceJobSerializer(serializers.ModelSerializer):
    quotes = QuoteSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    posted_by_name = serializers.CharField(source='posted_by.get_full_name', read_only=True)
    provider_name = serializers.CharField(source='assigned_provider.get_full_name', read_only=True)

    class Meta:
        model = ServiceJob
        fields = [
            'id', 'posted_by', 'posted_by_name', 'category', 'category_name', 'maintenance_request',
            'title', 'description', 'county', 'town', 'budget_estimate', 'status',
            'assigned_provider', 'provider_name', 'scheduled_date', 'completed_at',
            'quotes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'posted_by', 'status', 'assigned_provider', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['posted_by'] = self.context['request'].user
        return super().create(validated_data)


class ServiceProviderProfileSerializer(serializers.ModelSerializer):
    average_rating = serializers.FloatField(read_only=True)
    name = serializers.CharField(source='user.get_full_name', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    categories_detail = ServiceCategorySerializer(source='categories', many=True, read_only=True)

    class Meta:
        model = ServiceProviderProfile
        fields = [
            'id', 'user', 'name', 'phone_number', 'categories', 'categories_detail',
            'bio', 'years_experience', 'is_available', 'service_counties', 'average_rating',
        ]
        read_only_fields = ['id', 'user']


class PublicServiceProviderSerializer(serializers.ModelSerializer):
    """
    Public-facing view of a provider for the marketing site's marketplace page -
    deliberately excludes phone_number and other contact PII that
    ServiceProviderProfileSerializer exposes for authenticated/internal use.
    """
    average_rating = serializers.FloatField(read_only=True)
    name = serializers.CharField(source='user.get_full_name', read_only=True)
    categories_detail = ServiceCategorySerializer(source='categories', many=True, read_only=True)
    is_verified = serializers.BooleanField(source='user.is_kyc_verified', read_only=True)

    class Meta:
        model = ServiceProviderProfile
        fields = [
            'id', 'name', 'categories_detail', 'bio', 'years_experience',
            'is_available', 'service_counties', 'average_rating', 'is_verified',
        ]
        read_only_fields = fields


class JobReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobReview
        fields = ['id', 'job', 'reviewer', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'reviewer', 'created_at']

    def create(self, validated_data):
        validated_data['reviewer'] = self.context['request'].user
        return super().create(validated_data)
