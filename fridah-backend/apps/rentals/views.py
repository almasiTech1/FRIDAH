from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone

from apps.users.permissions import IsLandlordOrAdmin, IsTenant, IsAdminRole
from apps.properties.models import Unit
from .models import (
    Lease, Invoice, MaintenanceRequest, LeaseRenewal, UtilityAccount, UtilityMeterReading, RentalApplication,
    AmenityCharge, AmenityExemption,
)
from .serializers import (
    LeaseSerializer, LeaseCreateSerializer, InvoiceSerializer,
    MaintenanceRequestSerializer, LeaseRenewalSerializer, LeaseRenewalOfferUpdateSerializer,
    LeaseRenewalRespondSerializer, UtilityAccountSerializer, UtilityMeterReadingSerializer,
    RentalApplicationSerializer, AmenityChargeSerializer, AmenityExemptionSerializer,
)
from . import services


def success(data=None, message="OK", status_code=status.HTTP_200_OK):
    return Response({'success': True, 'message': message, 'data': data}, status=status_code)


class LeaseListCreateView(generics.ListCreateAPIView):
    filterset_fields = ['status']

    def get_serializer_class(self):
        return LeaseCreateSerializer if self.request.method == 'POST' else LeaseSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsLandlordOrAdmin()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'tenant':
            return Lease.objects.filter(tenant=user).order_by('-created_at')
        if user.role == 'admin' or user.is_staff:
            return Lease.objects.all().order_by('-created_at')
        from apps.agencies.permissions import agency_membership_for
        membership = agency_membership_for(user)
        if membership:
            from apps.agencies.models import PropertyManagementAssignment
            assigned_property_ids = PropertyManagementAssignment.objects.filter(
                agency=membership.agency, status=PropertyManagementAssignment.Status.ACTIVE
            ).values_list('property_id', flat=True)
            from django.db.models import Q
            return Lease.objects.filter(
                Q(landlord=user) | Q(unit__property_id__in=assigned_property_ids)
            ).distinct().order_by('-created_at')
        return Lease.objects.filter(landlord=user).order_by('-created_at')


class LeaseDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = LeaseSerializer
    queryset = Lease.objects.all()
    lookup_field = 'id'
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj = super().get_object()
        from apps.agencies.permissions import user_can_access_property
        user = self.request.user
        prop = obj.unit.property
        allowed = (
            user.role == 'admin' or user.is_staff or obj.tenant_id == user.id
            or user_can_access_property(user, prop)
        )
        if not allowed:
            raise PermissionDenied("You do not have access to this lease.")
        if self.request.method not in permissions.SAFE_METHODS:
            can_manage = (
                user.role == 'admin' or user.is_staff
                or user_can_access_property(user, prop, required_permission='tenants.manage')
            )
            if not can_manage:
                raise PermissionDenied("You do not have permission to modify this lease.")
        return obj


class LeaseActivateView(APIView):
    permission_classes = [IsLandlordOrAdmin]

    def post(self, request, id):
        lease = generics.get_object_or_404(Lease, id=id)
        lease.status = Lease.Status.ACTIVE
        lease.save(update_fields=['status'])
        lease.unit.status = Unit.Status.OCCUPIED
        lease.unit.save(update_fields=['status'])
        return success(message="Lease activated.")


class LeaseTerminateView(APIView):
    permission_classes = [IsLandlordOrAdmin]

    def post(self, request, id):
        lease = generics.get_object_or_404(Lease, id=id)
        lease.status = Lease.Status.TERMINATED
        lease.terminated_at = timezone.now()
        lease.termination_reason = request.data.get('reason', '')
        lease.save()
        lease.unit.status = Unit.Status.VACANT
        lease.unit.save(update_fields=['status'])
        return success(message="Lease terminated.")


class InvoiceListView(generics.ListAPIView):
    serializer_class = InvoiceSerializer
    filterset_fields = ['status', 'invoice_type']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'tenant':
            return Invoice.objects.filter(tenant=user).order_by('-created_at')
        if user.role == 'admin' or user.is_staff:
            return Invoice.objects.all().order_by('-created_at')
        from apps.agencies.permissions import agency_membership_for
        membership = agency_membership_for(user)
        if membership:
            from apps.agencies.models import PropertyManagementAssignment
            assigned_property_ids = PropertyManagementAssignment.objects.filter(
                agency=membership.agency, status=PropertyManagementAssignment.Status.ACTIVE
            ).values_list('property_id', flat=True)
            from django.db.models import Q
            return Invoice.objects.filter(
                Q(lease__landlord=user) | Q(lease__unit__property_id__in=assigned_property_ids)
            ).distinct().order_by('-created_at')
        return Invoice.objects.filter(lease__landlord=user).order_by('-created_at')


class InvoiceDetailView(generics.RetrieveAPIView):
    serializer_class = InvoiceSerializer
    queryset = Invoice.objects.all()
    lookup_field = 'id'
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj = super().get_object()
        from apps.agencies.permissions import user_can_access_property
        user = self.request.user
        allowed = (
            user.role == 'admin' or user.is_staff or obj.tenant_id == user.id
            or user_can_access_property(user, obj.lease.unit.property)
        )
        if not allowed:
            raise PermissionDenied("You do not have access to this invoice.")
        return obj


class MaintenanceRequestListCreateView(generics.ListCreateAPIView):
    serializer_class = MaintenanceRequestSerializer
    filterset_fields = ['status', 'priority', 'category']

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsTenant()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'tenant':
            return MaintenanceRequest.objects.filter(tenant=user).order_by('-created_at')
        if user.role == 'service_provider':
            return MaintenanceRequest.objects.filter(assigned_provider=user).order_by('-created_at')
        if user.role == 'admin' or user.is_staff:
            return MaintenanceRequest.objects.all().order_by('-created_at')
        from apps.agencies.permissions import agency_membership_for
        membership = agency_membership_for(user)
        if membership:
            from apps.agencies.models import PropertyManagementAssignment
            assigned_property_ids = PropertyManagementAssignment.objects.filter(
                agency=membership.agency, status=PropertyManagementAssignment.Status.ACTIVE
            ).values_list('property_id', flat=True)
            from django.db.models import Q
            return MaintenanceRequest.objects.filter(
                Q(unit__property__landlord=user) | Q(unit__property_id__in=assigned_property_ids)
            ).distinct().order_by('-created_at')
        return MaintenanceRequest.objects.filter(unit__property__landlord=user).order_by('-created_at')


class MaintenanceRequestDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = MaintenanceRequestSerializer
    queryset = MaintenanceRequest.objects.all()
    lookup_field = 'id'
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj = super().get_object()
        from apps.agencies.permissions import user_can_access_property
        user = self.request.user
        allowed = (
            user.role == 'admin' or user.is_staff or obj.tenant_id == user.id
            or obj.assigned_provider_id == user.id
            or user_can_access_property(user, obj.unit.property)
        )
        if not allowed:
            raise PermissionDenied("You do not have access to this maintenance request.")
        if self.request.method not in permissions.SAFE_METHODS:
            can_manage = (
                user.role == 'admin' or user.is_staff or obj.tenant_id == user.id
                or user_can_access_property(user, obj.unit.property, required_permission='maintenance.manage')
            )
            if not can_manage:
                raise PermissionDenied("You do not have permission to update this maintenance request.")
        return obj


class MaintenanceAssignView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id):
        from apps.agencies.permissions import user_can_access_property
        req = generics.get_object_or_404(MaintenanceRequest, id=id)
        user = request.user
        if not (user.role == 'admin' or user.is_staff
                or user_can_access_property(user, req.unit.property, required_permission='maintenance.manage')):
            raise PermissionDenied("You do not have permission to assign this maintenance request.")
        req.assigned_provider_id = request.data.get('provider_id')
        req.status = MaintenanceRequest.Status.ASSIGNED
        req.save()
        return success(message="Provider assigned.")


class MaintenanceResolveView(APIView):
    def post(self, request, id):
        req = generics.get_object_or_404(MaintenanceRequest, id=id)
        req.status = MaintenanceRequest.Status.RESOLVED
        req.resolved_at = timezone.now()
        req.resolution_notes = request.data.get('notes', '')
        req.save()
        return success(message="Maintenance request resolved.")


class LeaseRenewalListView(generics.ListAPIView):
    serializer_class = LeaseRenewalSerializer
    filterset_fields = ['status']

    def get_queryset(self):
        user = self.request.user
        qs = LeaseRenewal.objects.select_related('lease', 'lease__tenant', 'lease__unit', 'lease__unit__property')
        if user.role == 'tenant':
            return qs.filter(lease__tenant=user).order_by('-created_at')
        if user.role == 'admin' or user.is_staff:
            return qs.order_by('-created_at')
        from apps.agencies.permissions import agency_membership_for
        membership = agency_membership_for(user)
        if membership:
            from apps.agencies.models import PropertyManagementAssignment
            assigned_property_ids = PropertyManagementAssignment.objects.filter(
                agency=membership.agency, status=PropertyManagementAssignment.Status.ACTIVE
            ).values_list('property_id', flat=True)
            from django.db.models import Q
            return qs.filter(
                Q(lease__landlord=user) | Q(lease__unit__property_id__in=assigned_property_ids)
            ).distinct().order_by('-created_at')
        return qs.filter(lease__landlord=user).order_by('-created_at')


class LeaseRenewalDetailView(generics.RetrieveUpdateAPIView):
    """Landlord or agency staff with tenants.manage rights can PATCH proposed terms before the tenant responds."""
    queryset = LeaseRenewal.objects.all()
    lookup_field = 'id'
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        return LeaseRenewalOfferUpdateSerializer if self.request.method in ('PATCH', 'PUT') else LeaseRenewalSerializer

    def get_object(self):
        obj = super().get_object()
        from apps.agencies.permissions import user_can_access_property
        user = self.request.user
        prop = obj.lease.unit.property
        allowed = user.role == 'admin' or user.is_staff or obj.lease.tenant_id == user.id or user_can_access_property(user, prop)
        if not allowed:
            raise PermissionDenied("You do not have access to this lease renewal.")
        if self.request.method in ('PATCH', 'PUT'):
            can_manage = (
                user.role == 'admin' or user.is_staff
                or user_can_access_property(user, prop, required_permission='tenants.manage')
            )
            if not can_manage:
                raise PermissionDenied("You do not have permission to modify this renewal offer.")
        return obj


class LeaseRenewalRespondView(APIView):
    """Tenant accepts or declines a renewal offer with one tap."""
    permission_classes = [IsTenant]

    def post(self, request, id):
        from .services import accept_lease_renewal, decline_lease_renewal

        renewal = generics.get_object_or_404(LeaseRenewal, id=id, lease__tenant=request.user)
        if renewal.status != LeaseRenewal.Status.PENDING:
            return Response(
                {'success': False, 'error': {'message': 'This renewal offer has already been responded to.'}},
                status=400,
            )

        serializer = LeaseRenewalRespondSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data['accept']:
            new_lease = accept_lease_renewal(renewal)
            return success(
                {'renewal': LeaseRenewalSerializer(renewal).data, 'new_lease': LeaseSerializer(new_lease).data},
                message="Lease renewed successfully.",
            )
        else:
            decline_lease_renewal(renewal, serializer.validated_data.get('decline_reason', ''))
            return success(LeaseRenewalSerializer(renewal).data, message="Renewal declined.")


class UtilityAccountListCreateView(generics.ListCreateAPIView):
    """Landlord or agency staff (finance.manage) manages which utilities are tracked per unit."""
    serializer_class = UtilityAccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = UtilityAccount.objects.select_related('unit', 'unit__property')
        if user.role == 'admin' or user.is_staff:
            return qs
        from apps.agencies.permissions import agencies_staffed_by
        agency_ids = agencies_staffed_by(user).values_list('id', flat=True)
        from django.db.models import Q
        return qs.filter(
            Q(unit__property__landlord=user)
            | Q(unit__property__management_assignments__agency_id__in=agency_ids,
                unit__property__management_assignments__status='active')
        ).distinct()

    def perform_create(self, serializer):
        from apps.agencies.permissions import user_can_access_property
        from apps.properties.models import Unit
        user = self.request.user
        unit = generics.get_object_or_404(Unit, id=self.request.data.get('unit'))
        if not (user.role == 'admin' or user.is_staff
                or user_can_access_property(user, unit.property, required_permission='finance.manage')):
            raise PermissionDenied("You do not have permission to manage utilities for this property.")
        serializer.save()


class UtilityAccountDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UtilityAccountSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    queryset = UtilityAccount.objects.all()

    def get_object(self):
        obj = super().get_object()
        from apps.agencies.permissions import user_can_access_property
        user = self.request.user
        if not (user.role == 'admin' or user.is_staff
                or user_can_access_property(user, obj.unit.property, required_permission='finance.manage')):
            raise PermissionDenied("You do not have permission to manage this utility account.")
        return obj


class UtilityMeterReadingListCreateView(generics.ListCreateAPIView):
    """
    Recording a reading here automatically generates the corresponding utility invoice
    for the tenant if the account is metered with a rate configured (see
    services.record_utility_reading) - landlords and agency finance/property staff don't
    need a separate billing step.
    """
    serializer_class = UtilityMeterReadingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = UtilityMeterReading.objects.select_related('utility_account')
        account_id = self.request.query_params.get('utility_account')
        if account_id:
            qs = qs.filter(utility_account_id=account_id)
        if user.role == 'admin' or user.is_staff:
            return qs
        from apps.agencies.permissions import agencies_staffed_by
        agency_ids = agencies_staffed_by(user).values_list('id', flat=True)
        from django.db.models import Q
        return qs.filter(
            Q(utility_account__unit__property__landlord=user)
            | Q(utility_account__unit__property__management_assignments__agency_id__in=agency_ids,
                utility_account__unit__property__management_assignments__status='active')
        ).distinct()

    def create(self, request, *args, **kwargs):
        from .models import UtilityAccount
        from .services import record_utility_reading
        from apps.agencies.permissions import user_can_access_property

        account = generics.get_object_or_404(UtilityAccount, id=request.data.get('utility_account'))
        user = request.user
        if not (user.role == 'admin' or user.is_staff
                or user_can_access_property(user, account.unit.property, required_permission='finance.manage')):
            raise PermissionDenied("You can only record readings for units you own or manage.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reading, invoice = record_utility_reading(
            utility_account=account,
            reading_value=serializer.validated_data['reading_value'],
            reading_date=serializer.validated_data['reading_date'],
            recorded_by=request.user,
            photo=serializer.validated_data.get('photo'),
        )
        message = "Reading recorded." + (f" Invoice generated for KES {invoice.amount}." if invoice else "")
        return success(UtilityMeterReadingSerializer(reading).data, message=message, status_code=201)


class UnitApplyView(APIView):
    """Tenant applies to rent a specific vacant unit - this is the missing piece:
    previously listings were browsable but there was no way for a tenant to act
    on one at all."""
    permission_classes = [IsTenant]

    def post(self, request, unit_id):
        unit = generics.get_object_or_404(Unit, id=unit_id)
        from django.utils.dateparse import parse_date
        move_in_raw = request.data.get('preferred_move_in_date')
        try:
            application = services.submit_rental_application(
                unit=unit, tenant=request.user,
                message=request.data.get('message', ''),
                preferred_move_in_date=parse_date(move_in_raw) if move_in_raw else None,
            )
        except ValueError as e:
            return Response({'success': False, 'error': {'message': str(e)}}, status=400)
        return success(RentalApplicationSerializer(application).data, message="Application submitted.", status_code=201)


class RentalApplicationListView(generics.ListAPIView):
    """Tenants see their own applications; landlords/agency staff/admin see
    applications for properties they can access."""
    serializer_class = RentalApplicationSerializer
    filterset_fields = ['status']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin' or user.is_staff:
            return RentalApplication.objects.all().order_by('-created_at')
        if user.role == 'tenant':
            return RentalApplication.objects.filter(tenant=user).order_by('-created_at')
        from apps.agencies.permissions import properties_visible_to
        return RentalApplication.objects.filter(
            unit__property__in=properties_visible_to(user)
        ).order_by('-created_at')


class RentalApplicationApproveView(APIView):
    def post(self, request, id):
        application = generics.get_object_or_404(RentalApplication, id=id)
        from apps.agencies.permissions import user_can_access_property
        if not user_can_access_property(request.user, application.unit.property, required_permission='tenants.manage'):
            raise PermissionDenied("You cannot review this application.")

        try:
            from django.utils.dateparse import parse_date
            start_date = request.data.get('start_date')
            lease = services.approve_rental_application(
                application, reviewed_by=request.user,
                rent_amount=request.data.get('rent_amount'),
                deposit_amount=request.data.get('deposit_amount'),
                start_date=parse_date(start_date) if start_date else None,
                rent_due_day=request.data.get('rent_due_day', 5),
            )
        except ValueError as e:
            return Response({'success': False, 'error': {'message': str(e)}}, status=400)
        return success(
            {'application': RentalApplicationSerializer(application).data, 'lease': LeaseSerializer(lease).data},
            message="Application approved - lease created.",
        )


class RentalApplicationRejectView(APIView):
    def post(self, request, id):
        application = generics.get_object_or_404(RentalApplication, id=id)
        from apps.agencies.permissions import user_can_access_property
        if not user_can_access_property(request.user, application.unit.property, required_permission='tenants.manage'):
            raise PermissionDenied("You cannot review this application.")

        try:
            services.reject_rental_application(application, reviewed_by=request.user, reason=request.data.get('reason', ''))
        except ValueError as e:
            return Response({'success': False, 'error': {'message': str(e)}}, status=400)
        return success(RentalApplicationSerializer(application).data, message="Application rejected.")


class RentalApplicationWithdrawView(APIView):
    permission_classes = [IsTenant]

    def post(self, request, id):
        application = generics.get_object_or_404(RentalApplication, id=id)
        try:
            services.withdraw_rental_application(application, tenant=request.user)
        except ValueError as e:
            return Response({'success': False, 'error': {'message': str(e)}}, status=400)
        return success(RentalApplicationSerializer(application).data, message="Application withdrawn.")


class MaintenanceImageUploadView(APIView):
    """
    Attach a photo to an existing maintenance request - the request-images
    relationship (MaintenanceRequest.images) was already displayed in the API,
    but there was no endpoint to actually create one. The tenant who filed the
    request, staff with maintenance.manage access to the property, or admin can
    attach photos (a landlord/provider photographing the completed repair is a
    real use case too, not just the tenant's original report).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id):
        from apps.agencies.permissions import user_can_access_property
        from .models import MaintenanceImage

        req = generics.get_object_or_404(MaintenanceRequest, id=id)
        user = request.user
        allowed = (
            user.role == 'admin' or user.is_staff or req.tenant_id == user.id
            or req.assigned_provider_id == user.id
            or user_can_access_property(user, req.unit.property, required_permission='maintenance.manage')
        )
        if not allowed:
            raise PermissionDenied("You do not have permission to attach photos to this request.")

        image = request.FILES.get('image')
        if not image:
            return Response({'success': False, 'error': {'message': 'An image file is required.'}}, status=400)

        photo = MaintenanceImage.objects.create(request=req, image=image)
        from .serializers import MaintenanceImageSerializer
        return success(MaintenanceImageSerializer(photo).data, message="Photo attached.", status_code=201)


# --------------------------------------------------------------------------- amenity charges
def _can_manage_property(user, prop):
    from apps.agencies.permissions import user_can_access_property
    return user.role == 'admin' or user.is_staff or user_can_access_property(user, prop, required_permission='property.manage')


class AmenityChargeListCreateView(generics.ListCreateAPIView):
    """Managers/owners/admins configure amenity charges; tenants never see this configuration."""
    serializer_class = AmenityChargeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['property', 'is_active', 'frequency']

    def get_queryset(self):
        from apps.agencies.permissions import properties_visible_to
        user = self.request.user
        if user.role == 'tenant':
            return AmenityCharge.objects.none()
        return AmenityCharge.objects.filter(property__in=properties_visible_to(user)).prefetch_related('units')

    def perform_create(self, serializer):
        prop = serializer.validated_data['property']
        if not _can_manage_property(self.request.user, prop):
            raise PermissionDenied('You cannot configure charges for this property.')
        serializer.save(created_by=self.request.user)


class AmenityChargeDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = AmenityChargeSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        from apps.agencies.permissions import properties_visible_to
        if self.request.user.role == 'tenant':
            return AmenityCharge.objects.none()
        return AmenityCharge.objects.filter(property__in=properties_visible_to(self.request.user))

    def perform_update(self, serializer):
        if not _can_manage_property(self.request.user, serializer.instance.property):
            raise PermissionDenied('You cannot change charges for this property.')
        serializer.save()


class AmenityBillNowView(APIView):
    """Run billing for one charge now (the daily task does this automatically; idempotent)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id):
        from . import amenities
        charge = generics.get_object_or_404(AmenityCharge, id=id)
        if not _can_manage_property(request.user, charge.property):
            raise PermissionDenied('You cannot bill this charge.')
        created, skipped = amenities.generate_for_charge(charge)
        return success({'created': created, 'skipped': skipped}, 'Billing run complete.')


class AmenityExemptionCreateView(generics.CreateAPIView):
    serializer_class = AmenityExemptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        charge, lease = serializer.validated_data['charge'], serializer.validated_data['lease']
        if lease.unit.property_id != charge.property_id:
            raise PermissionDenied('That lease is not on this charge\'s property.')
        if not _can_manage_property(self.request.user, charge.property):
            raise PermissionDenied('You cannot grant exemptions for this property.')
        if not serializer.validated_data['reason'].strip():
            raise PermissionDenied('A reason is required.')
        serializer.save(granted_by=self.request.user)


class AmenityInvoiceWaiveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id):
        from django.core.exceptions import ValidationError as DjangoValidationError
        from . import amenities
        invoice = generics.get_object_or_404(Invoice.objects.select_related('lease__unit__property'), id=id)
        if not _can_manage_property(request.user, invoice.lease.unit.property):
            raise PermissionDenied('You cannot waive this invoice.')
        try:
            amenities.waive_invoice(invoice, request.user, request.data.get('reason', ''))
        except DjangoValidationError as e:
            return Response({'success': False, 'error': {'message': ' '.join(e.messages)}}, status=400)
        return success(message='Invoice waived.')
