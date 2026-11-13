import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Listing(models.Model):
    """A hotel / BnB / short-stay property."""
    class ListingType(models.TextChoices):
        HOTEL = 'hotel', 'Hotel'
        BNB = 'bnb', 'BnB'
        APARTMENT_STAY = 'apartment_stay', 'Serviced Apartment'
        VILLA = 'villa', 'Villa'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        PENDING_APPROVAL = 'pending_approval', 'Pending Approval'
        SUSPENDED = 'suspended', 'Suspended'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='listings')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    listing_type = models.CharField(max_length=20, choices=ListingType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_APPROVAL)

    county = models.CharField(max_length=50)
    town = models.CharField(max_length=100)
    address_detail = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, validators=[MinValueValidator(-180), MaxValueValidator(180)])

    amenities = models.JSONField(default=list, blank=True)
    check_in_time = models.TimeField(default='14:00')
    check_out_time = models.TimeField(default='11:00')
    cancellation_policy = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'listings'
        indexes = [models.Index(fields=['county', 'town']), models.Index(fields=['status'])]

    def __str__(self):
        return self.name


class ListingImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='listing_images/')
    is_primary = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'listing_images'
        ordering = ['order']


class RoomType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='room_types')
    name = models.CharField(max_length=100)  # "Deluxe Room", "Studio"
    description = models.TextField(blank=True)
    max_occupancy = models.PositiveSmallIntegerField(default=2)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    total_rooms = models.PositiveIntegerField(default=1)
    amenities = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'room_types'

    def __str__(self):
        return f"{self.listing.name} - {self.name}"


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT = 'pending_payment', 'Pending Payment'
        CONFIRMED = 'confirmed', 'Confirmed'
        CHECKED_IN = 'checked_in', 'Checked In'
        CHECKED_OUT = 'checked_out', 'Checked Out'
        CANCELLED = 'cancelled', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    guest = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='bookings')
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name='bookings')
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='host_bookings')

    check_in_date = models.DateField()
    check_out_date = models.DateField()
    num_guests = models.PositiveSmallIntegerField(default=1)
    num_rooms = models.PositiveSmallIntegerField(default=1)

    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_PAYMENT)

    booking_reference = models.CharField(max_length=20, unique=True)
    special_requests = models.TextField(blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bookings'
        indexes = [models.Index(fields=['status']), models.Index(fields=['check_in_date', 'check_out_date'])]

    def __str__(self):
        return self.booking_reference

    @property
    def nights(self):
        return (self.check_out_date - self.check_in_date).days

    def save(self, *args, **kwargs):
        if not self.booking_reference:
            self.booking_reference = f"BK-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class BookingReview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='review')
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'booking_reviews'
