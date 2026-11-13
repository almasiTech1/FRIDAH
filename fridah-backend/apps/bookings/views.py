from rest_framework import generics, permissions, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone

from apps.users.permissions import IsHotelOwner, IsAdminRole
from .models import Listing, RoomType, Booking, BookingReview
from .serializers import (
    ListingListSerializer, ListingDetailSerializer, ListingCreateSerializer,
    RoomTypeSerializer, BookingSerializer, BookingCreateSerializer, BookingReviewSerializer,
)


def success(data=None, message="OK", status_code=status.HTTP_200_OK):
    return Response({'success': True, 'message': message, 'data': data}, status=status_code)


class ListingListCreateView(generics.ListCreateAPIView):
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['county', 'town', 'listing_type', 'status']
    search_fields = ['name', 'town', 'county']

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsHotelOwner()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        return ListingCreateSerializer if self.request.method == 'POST' else ListingListSerializer

    def get_queryset(self):
        user = self.request.user
        if self.request.method == 'GET' and user.is_authenticated and user.role in ('hotel_owner', 'admin'):
            if user.role == 'hotel_owner':
                return Listing.objects.filter(host=user).order_by('-created_at')
            return Listing.objects.all().order_by('-created_at')
        return Listing.objects.filter(status=Listing.Status.ACTIVE).order_by('-created_at')


class ListingDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ListingDetailSerializer
    queryset = Listing.objects.all()
    lookup_field = 'id'

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [IsHotelOwner()]


class ListingApprovalView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, id):
        listing = generics.get_object_or_404(Listing, id=id)
        action = request.data.get('action')
        mapping = {'approve': Listing.Status.ACTIVE, 'suspend': Listing.Status.SUSPENDED}
        if action not in mapping:
            return Response({'success': False, 'error': {'message': 'Invalid action'}}, status=400)
        listing.status = mapping[action]
        listing.save(update_fields=['status'])
        return success(message=f"Listing {action}d.")


class RoomTypeListCreateView(generics.ListCreateAPIView):
    serializer_class = RoomTypeSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsHotelOwner()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        return RoomType.objects.filter(listing_id=self.kwargs['listing_id'])

    def perform_create(self, serializer):
        serializer.save(listing_id=self.kwargs['listing_id'])


class RoomTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = RoomTypeSerializer
    queryset = RoomType.objects.all()
    lookup_field = 'id'
    permission_classes = [IsHotelOwner]


class RoomAvailabilityView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, room_type_id):
        from django.db.models import Sum
        check_in = request.query_params.get('check_in')
        check_out = request.query_params.get('check_out')
        room_type = generics.get_object_or_404(RoomType, id=room_type_id)
        # Sum num_rooms, not count bookings: a single booking can reserve multiple rooms
        # of the same type, so counting bookings understates how many rooms are taken.
        booked_rooms = Booking.objects.filter(
            room_type=room_type,
            status__in=[Booking.Status.CONFIRMED, Booking.Status.CHECKED_IN],
            check_in_date__lt=check_out,
            check_out_date__gt=check_in,
        ).aggregate(total=Sum('num_rooms'))['total'] or 0 if check_in and check_out else 0
        available = max(room_type.total_rooms - booked_rooms, 0)
        return success({'available_rooms': available, 'total_rooms': room_type.total_rooms})


class AvailabilityCalendarView(APIView):
    """
    Visual calendar data: for every day in the requested range, how many rooms of each
    room type are booked vs available. Essential for hotel/BnB owners managing bookings
    across multiple room types at once.
    """
    def get(self, request, listing_id):
        from datetime import timedelta
        from django.db.models import Sum
        from django.utils.dateparse import parse_date

        listing = generics.get_object_or_404(Listing, id=listing_id)
        start = parse_date(request.query_params.get('start')) or timezone.now().date()
        end = parse_date(request.query_params.get('end')) or (start + timedelta(days=30))

        if end <= start:
            return Response({'success': False, 'error': {'message': "'end' must be after 'start'."}}, status=400)
        if (end - start).days > 366:
            return Response({'success': False, 'error': {'message': "Range too large - max 366 days."}}, status=400)

        room_types = list(listing.room_types.all())
        bookings = Booking.objects.filter(
            listing=listing,
            status__in=[Booking.Status.CONFIRMED, Booking.Status.CHECKED_IN],
            check_in_date__lt=end,
            check_out_date__gt=start,
        ).values('room_type_id', 'check_in_date', 'check_out_date', 'num_rooms')

        days = []
        current = start
        while current < end:
            day_data = []
            for rt in room_types:
                booked = sum(
                    b['num_rooms'] for b in bookings
                    if b['room_type_id'] == rt.id and b['check_in_date'] <= current < b['check_out_date']
                )
                day_data.append({
                    'room_type_id': str(rt.id),
                    'room_type_name': rt.name,
                    'total_rooms': rt.total_rooms,
                    'booked_rooms': booked,
                    'available_rooms': max(rt.total_rooms - booked, 0),
                })
            days.append({'date': current.isoformat(), 'room_types': day_data})
            current += timedelta(days=1)

        return success({
            'listing_id': str(listing.id),
            'listing_name': listing.name,
            'start': start.isoformat(),
            'end': end.isoformat(),
            'days': days,
        })


class BookingListCreateView(generics.ListCreateAPIView):
    filterset_fields = ['status']

    def get_serializer_class(self):
        return BookingCreateSerializer if self.request.method == 'POST' else BookingSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'hotel_owner':
            return Booking.objects.filter(host=user).order_by('-created_at')
        if user.role == 'admin':
            return Booking.objects.all().order_by('-created_at')
        return Booking.objects.filter(guest=user).order_by('-created_at')


class BookingDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = BookingSerializer
    queryset = Booking.objects.all()
    lookup_field = 'id'


class BookingCancelView(APIView):
    def post(self, request, id):
        booking = generics.get_object_or_404(Booking, id=id)
        booking.status = Booking.Status.CANCELLED
        booking.cancelled_at = timezone.now()
        booking.cancellation_reason = request.data.get('reason', '')
        booking.save()
        return success(message="Booking cancelled.")


class BookingCheckInView(APIView):
    permission_classes = [IsHotelOwner]

    def post(self, request, id):
        booking = generics.get_object_or_404(Booking, id=id)
        booking.status = Booking.Status.CHECKED_IN
        booking.save(update_fields=['status'])
        return success(message="Guest checked in.")


class BookingCheckOutView(APIView):
    permission_classes = [IsHotelOwner]

    def post(self, request, id):
        booking = generics.get_object_or_404(Booking, id=id)
        booking.status = Booking.Status.CHECKED_OUT
        booking.save(update_fields=['status'])
        return success(message="Guest checked out.")


class BookingReviewCreateView(generics.CreateAPIView):
    serializer_class = BookingReviewSerializer
