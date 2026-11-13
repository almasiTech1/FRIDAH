from rest_framework import serializers
from .models import Listing, ListingImage, RoomType, Booking, BookingReview
from common.fields import LatitudeField, LongitudeField


class ListingImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingImage
        fields = ['id', 'image', 'is_primary', 'order']


class RoomTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomType
        fields = ['id', 'listing', 'name', 'description', 'max_occupancy', 'price_per_night', 'total_rooms', 'amenities']
        read_only_fields = ['id']


class ListingListSerializer(serializers.ModelSerializer):
    primary_image = serializers.SerializerMethodField()
    min_price = serializers.SerializerMethodField()
    host_name = serializers.CharField(source='host.get_full_name', read_only=True)

    class Meta:
        model = Listing
        fields = [
            'id', 'name', 'listing_type', 'status', 'county', 'town', 'amenities',
            'primary_image', 'min_price', 'host', 'host_name', 'latitude', 'longitude', 'created_at',
        ]

    def get_primary_image(self, obj):
        img = obj.images.filter(is_primary=True).first() or obj.images.first()
        return img.image.url if img else None

    def get_min_price(self, obj):
        rt = obj.room_types.order_by('price_per_night').first()
        return rt.price_per_night if rt else None


class ListingDetailSerializer(serializers.ModelSerializer):
    images = ListingImageSerializer(many=True, read_only=True)
    room_types = RoomTypeSerializer(many=True, read_only=True)
    host_name = serializers.CharField(source='host.get_full_name', read_only=True)
    host_phone = serializers.CharField(source='host.phone_number', read_only=True)

    class Meta:
        model = Listing
        fields = [
            'id', 'host', 'host_name', 'host_phone', 'name', 'description', 'listing_type',
            'status', 'county', 'town', 'address_detail', 'latitude', 'longitude', 'amenities',
            'check_in_time', 'check_out_time', 'cancellation_policy', 'images', 'room_types',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'host', 'created_at', 'updated_at']


class ListingCreateSerializer(serializers.ModelSerializer):
    latitude = LatitudeField()
    longitude = LongitudeField()

    class Meta:
        model = Listing
        fields = [
            'id', 'name', 'description', 'listing_type', 'county', 'town', 'address_detail',
            'latitude', 'longitude', 'amenities', 'check_in_time', 'check_out_time', 'cancellation_policy',
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        validated_data['host'] = self.context['request'].user
        validated_data['status'] = Listing.Status.PENDING_APPROVAL
        return super().create(validated_data)


class BookingReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingReview
        fields = ['id', 'booking', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'created_at']


class BookingSerializer(serializers.ModelSerializer):
    guest_name = serializers.CharField(source='guest.get_full_name', read_only=True)
    listing_name = serializers.CharField(source='listing.name', read_only=True)
    room_type_name = serializers.CharField(source='room_type.name', read_only=True)
    nights = serializers.IntegerField(read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'guest', 'guest_name', 'listing', 'listing_name', 'room_type', 'room_type_name',
            'host', 'check_in_date', 'check_out_date', 'nights', 'num_guests', 'num_rooms',
            'total_amount', 'amount_paid', 'status', 'booking_reference', 'special_requests',
            'cancelled_at', 'cancellation_reason', 'created_at',
        ]
        read_only_fields = ['id', 'host', 'booking_reference', 'amount_paid', 'status', 'created_at']


class BookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['id', 'listing', 'room_type', 'check_in_date', 'check_out_date', 'num_guests', 'num_rooms', 'special_requests']
        read_only_fields = ['id']

    def validate(self, attrs):
        if attrs['check_out_date'] <= attrs['check_in_date']:
            raise serializers.ValidationError("Check-out date must be after check-in date.")
        return attrs

    def create(self, validated_data):
        room_type = validated_data['room_type']
        nights = (validated_data['check_out_date'] - validated_data['check_in_date']).days
        validated_data['total_amount'] = room_type.price_per_night * nights * validated_data.get('num_rooms', 1)
        validated_data['guest'] = self.context['request'].user
        validated_data['host'] = room_type.listing.host
        validated_data['status'] = Booking.Status.PENDING_PAYMENT
        return super().create(validated_data)
