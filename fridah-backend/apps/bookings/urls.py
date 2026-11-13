from django.urls import path
from . import views

urlpatterns = [
    path('listings/', views.ListingListCreateView.as_view(), name='listing_list'),
    path('listings/<uuid:id>/', views.ListingDetailView.as_view(), name='listing_detail'),
    path('listings/<uuid:id>/approval/', views.ListingApprovalView.as_view(), name='listing_approval'),
    path('listings/<uuid:listing_id>/room-types/', views.RoomTypeListCreateView.as_view(), name='room_type_list'),
    path('room-types/<uuid:id>/', views.RoomTypeDetailView.as_view(), name='room_type_detail'),
    path('room-types/<uuid:room_type_id>/availability/', views.RoomAvailabilityView.as_view(), name='room_availability'),
    path('listings/<uuid:listing_id>/calendar/', views.AvailabilityCalendarView.as_view(), name='availability_calendar'),

    path('bookings/', views.BookingListCreateView.as_view(), name='booking_list'),
    path('bookings/<uuid:id>/', views.BookingDetailView.as_view(), name='booking_detail'),
    path('bookings/<uuid:id>/cancel/', views.BookingCancelView.as_view(), name='booking_cancel'),
    path('bookings/<uuid:id>/check-in/', views.BookingCheckInView.as_view(), name='booking_checkin'),
    path('bookings/<uuid:id>/check-out/', views.BookingCheckOutView.as_view(), name='booking_checkout'),
    path('bookings/reviews/', views.BookingReviewCreateView.as_view(), name='booking_review'),
]
