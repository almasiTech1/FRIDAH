from django.utils import timezone
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from apps.users.permissions import IsTenant, IsLandlordOrAdmin
from .models import Visitor
from .serializers import VisitorSerializer, VisitorQRScanSerializer


def success(data=None, message="OK", status_code=200):
    return Response({'success': True, 'message': message, 'data': data}, status=status_code)


class VisitorListCreateView(generics.ListCreateAPIView):
    """Tenants pre-register expected visitors for their own unit; landlords see visitors across their properties."""
    serializer_class = VisitorSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsTenant()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = Visitor.objects.select_related('unit', 'unit__property', 'registered_by')
        if user.role == 'tenant':
            return qs.filter(registered_by=user)
        if user.role == 'landlord':
            return qs.filter(unit__property__landlord=user)
        return qs  # admin

    def perform_create(self, serializer):
        from apps.rentals.models import Lease

        unit = serializer.validated_data['unit']
        has_active_lease = Lease.objects.filter(
            unit=unit, tenant=self.request.user, status=Lease.Status.ACTIVE
        ).exists()
        if not has_active_lease:
            raise PermissionDenied("You can only register visitors for a unit you currently lease.")
        serializer.save()


class VisitorQRCheckInView(APIView):
    """Security/landlord scans the visitor's QR code to check them in."""
    permission_classes = [IsLandlordOrAdmin]

    def post(self, request):
        serializer = VisitorQRScanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        visitor = generics.get_object_or_404(Visitor, qr_token=serializer.validated_data['qr_token'])

        if visitor.status == Visitor.Status.CHECKED_IN:
            return Response({'success': False, 'error': {'message': 'This visitor is already checked in.'}}, status=400)
        if visitor.status in (Visitor.Status.CHECKED_OUT, Visitor.Status.CANCELLED, Visitor.Status.EXPIRED):
            return Response(
                {'success': False, 'error': {'message': f'This QR code is no longer valid ({visitor.status}).'}},
                status=400,
            )
        if visitor.expected_date < timezone.now().date():
            visitor.status = Visitor.Status.EXPIRED
            visitor.save(update_fields=['status'])
            return Response({'success': False, 'error': {'message': 'This visitor pass has expired.'}}, status=400)

        visitor.status = Visitor.Status.CHECKED_IN
        visitor.checked_in_at = timezone.now()
        visitor.checked_in_by = request.user
        visitor.save(update_fields=['status', 'checked_in_at', 'checked_in_by'])
        return success(VisitorSerializer(visitor).data, message=f"{visitor.visitor_name} checked in.")


class VisitorQRCheckOutView(APIView):
    """Security/landlord scans the same QR code again on the visitor's way out."""
    permission_classes = [IsLandlordOrAdmin]

    def post(self, request):
        serializer = VisitorQRScanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        visitor = generics.get_object_or_404(Visitor, qr_token=serializer.validated_data['qr_token'])

        if visitor.status != Visitor.Status.CHECKED_IN:
            return Response(
                {'success': False, 'error': {'message': 'This visitor is not currently checked in.'}}, status=400,
            )

        visitor.status = Visitor.Status.CHECKED_OUT
        visitor.checked_out_at = timezone.now()
        visitor.checked_out_by = request.user
        visitor.save(update_fields=['status', 'checked_out_at', 'checked_out_by'])
        return success(VisitorSerializer(visitor).data, message=f"{visitor.visitor_name} checked out.")


class VisitorCancelView(APIView):
    """Tenant cancels a pre-registered visitor pass before it's used."""
    permission_classes = [IsTenant]

    def post(self, request, id):
        visitor = generics.get_object_or_404(Visitor, id=id, registered_by=request.user)
        if visitor.status != Visitor.Status.PRE_REGISTERED:
            return Response(
                {'success': False, 'error': {'message': 'Only a pre-registered (not yet used) pass can be cancelled.'}},
                status=400,
            )
        visitor.status = Visitor.Status.CANCELLED
        visitor.save(update_fields=['status'])
        return success(message="Visitor pass cancelled.")
