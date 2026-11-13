from rest_framework import serializers


class PropertySearchQuerySerializer(serializers.Serializer):
    query = serializers.CharField(max_length=500, min_length=3)


class RentEstimateRequestSerializer(serializers.Serializer):
    county = serializers.CharField(max_length=100)
    town = serializers.CharField(max_length=100, required=False, allow_blank=True)
    bedrooms = serializers.IntegerField(min_value=0, max_value=20)
    amenities = serializers.ListField(child=serializers.CharField(max_length=100), required=False, default=list)
    size_sqm = serializers.FloatField(required=False, allow_null=True)


class ListingGenerateFactsSerializer(serializers.Serializer):
    """Validated as a nested JSON string field alongside multipart image uploads."""
    property_type = serializers.CharField(required=False, allow_blank=True)
    bedrooms = serializers.IntegerField(required=False, allow_null=True)
    bathrooms = serializers.IntegerField(required=False, allow_null=True)
    county = serializers.CharField(required=False, allow_blank=True)
    town = serializers.CharField(required=False, allow_blank=True)
    estate = serializers.CharField(required=False, allow_blank=True)
    rent_amount = serializers.FloatField(required=False, allow_null=True)
    known_amenities = serializers.ListField(child=serializers.CharField(), required=False, default=list)


class MaintenanceTriageRequestSerializer(serializers.Serializer):
    description = serializers.CharField(required=False, allow_blank=True, default='')
