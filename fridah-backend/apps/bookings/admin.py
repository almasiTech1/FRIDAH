from django.contrib import admin
from .models import Listing, ListingImage, RoomType, Booking, BookingReview


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ('name', 'host', 'listing_type', 'status', 'town', 'county')
    list_filter = ('status', 'listing_type', 'county')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('booking_reference', 'guest', 'listing', 'check_in_date', 'check_out_date', 'status')
    list_filter = ('status',)
    search_fields = ('booking_reference',)


admin.site.register(ListingImage)
admin.site.register(RoomType)
admin.site.register(BookingReview)
