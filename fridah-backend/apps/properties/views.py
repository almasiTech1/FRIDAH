from rest_framework import generics, permissions, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError as DRFValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q

from apps.users.permissions import IsLandlordOrAdmin, IsAdminRole, IsLandlord
from .models import Property, Unit, SavedProperty, PropertyReview, PropertyDocument, PropertyApproval
from . import approvals
from .serializers import (
    PropertyListSerializer, PropertyDetailSerializer, PropertyCreateSerializer,
    UnitSerializer, SavedPropertySerializer, PropertyReviewSerializer, PropertyDocumentSerializer,
    PropertyApprovalSerializer,
)


def success(data=None, message="OK", status_code=status.HTTP_200_OK):
    return Response({'success': True, 'message': message, 'data': data}, status=status_code)


def _error(message, status_code=400):
    return Response({'success': False, 'error': {'message': message}}, status=status_code)


def _visible_property_or_404(user, prop):
    """Unapproved properties do not exist as far as the public / other users are concerned."""
    if not approvals.can_view_property(user, prop):
        raise NotFound('Property not found.')
    return prop


class PropertyListCreateView(generics.ListCreateAPIView):
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['county', 'town', 'property_type', 'status']
    search_fields = ['name', 'estate', 'town', 'county']
    ordering_fields = ['created_at', 'name']

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsLandlordOrAdmin()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        return PropertyCreateSerializer if self.request.method == 'POST' else PropertyListSerializer

    def get_queryset(self):
        qs = Property.objects.all()
        user = self.request.user
        if self.request.method == 'GET':
            if user.is_authenticated and (user.role in ('landlord', 'admin') or self._has_agency_access(user)):
                from apps.agencies.permissions import properties_visible_to
                return properties_visible_to(user).order_by('-created_at')
            # Public/tenant view: only active listings
            qs = qs.filter(status=Property.Status.ACTIVE)
            min_rent = self.request.query_params.get('min_rent')
            max_rent = self.request.query_params.get('max_rent')
            bedrooms = self.request.query_params.get('bedrooms')
            if min_rent or max_rent or bedrooms:
                unit_q = Q()
                if min_rent:
                    unit_q &= Q(units__rent_amount__gte=min_rent)
                if max_rent:
                    unit_q &= Q(units__rent_amount__lte=max_rent)
                if bedrooms:
                    unit_q &= Q(units__bedrooms=bedrooms)
                qs = qs.filter(unit_q).distinct()
            return qs.order_by('-created_at')
        return qs

    @staticmethod
    def _has_agency_access(user):
        from apps.agencies.permissions import agency_membership_for
        return agency_membership_for(user) is not None


class PropertyAreaSummaryView(APIView):
    """
    Public: counts of active properties/vacant units grouped by county, powering the
    marketing site's "explore by area" section with real numbers instead of guesses.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from django.db.models import Count
        rows = (
            Property.objects.filter(status=Property.Status.ACTIVE)
            .values('county')
            .annotate(
                property_count=Count('id', distinct=True),
                vacant_units=Count('units', filter=Q(units__status='vacant'), distinct=True),
            )
            .order_by('-property_count')
        )
        return Response({
            'success': True,
            'data': [
                {'county': r['county'], 'property_count': r['property_count'], 'vacant_units': r['vacant_units']}
                for r in rows if r['county']
            ],
        })


class PropertyDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PropertyDetailSerializer
    queryset = Property.objects.all()
    lookup_field = 'id'

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_object(self):
        obj = super().get_object()
        if self.request.method == 'GET':
            _visible_property_or_404(self.request.user, obj)
        return obj

    def _check_can_manage(self, request, instance):
        from apps.agencies.permissions import user_can_access_property
        if request.user.role == 'admin' or request.user.is_staff:
            return
        if approvals.is_agent_submitter(request.user, instance):
            return
        if not user_can_access_property(request.user, instance, required_permission='property.manage'):
            raise PermissionDenied("You do not have permission to manage this property.")

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        self._check_can_manage(request, instance)
        self._before = {f: getattr(instance, f) for f in approvals.material_fields()}
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        instance = serializer.save()
        changed = [f for f, old in self._before.items() if getattr(instance, f) != old]
        # A material edit invalidates earlier approvals and returns the listing to review.
        approvals.register_edit(instance, self.request.user, changed)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self._check_can_manage(request, instance)
        return super().destroy(request, *args, **kwargs)


class PropertyApprovalView(APIView):
    """
    Administrator actions on a property.

    approve / reject / request_changes record the admin's decision in the approval
    workflow - approve does NOT publish on its own when the landlord's approval is also
    required. suspend / archive / reinstate change listing availability.
    """
    permission_classes = [IsAdminRole]

    def post(self, request, id):
        prop = generics.get_object_or_404(Property, id=id)
        action = request.data.get('action')
        comment = request.data.get('comment', '')
        decisions = {
            'approve': PropertyApproval.Decision.APPROVED,
            'reject': PropertyApproval.Decision.REJECTED,
            'request_changes': PropertyApproval.Decision.CHANGES_REQUESTED,
        }
        try:
            if action in decisions:
                if action == 'approve' and prop.review_state == Property.ReviewState.APPROVED \
                        and prop.status == Property.Status.SUSPENDED:
                    approvals.set_listing_status(prop, request.user, 'reinstate')
                else:
                    approvals.record_decision(prop, request.user, decisions[action], comment)
            elif action in ('suspend', 'archive', 'reinstate'):
                approvals.set_listing_status(prop, request.user, action)
            else:
                return _error('Invalid action')
        except DjangoValidationError as e:
            return _error(' '.join(e.messages))
        prop.refresh_from_db()
        return success(
            {'status': prop.status, 'review_state': prop.review_state,
             'missing_approvals': approvals.missing_approvals(prop) if prop.review_state != Property.ReviewState.APPROVED else []},
            message=f"Property {action} recorded.",
        )


class PropertyReviewDecisionView(APIView):
    """
    The landlord's (or an admin's) decision on a submitted property:
    POST {action: approve|reject|request_changes, comment}. Which party the decision counts
    for is derived from who is calling, never from the request body.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id):
        prop = generics.get_object_or_404(Property, id=id)
        mapping = {
            'approve': PropertyApproval.Decision.APPROVED,
            'reject': PropertyApproval.Decision.REJECTED,
            'request_changes': PropertyApproval.Decision.CHANGES_REQUESTED,
        }
        action = request.data.get('action')
        if action not in mapping:
            return _error('Invalid action')
        if not approvals.can_view_property(request.user, prop):
            raise NotFound('Property not found.')
        try:
            approvals.record_decision(prop, request.user, mapping[action], request.data.get('comment', ''))
        except DjangoValidationError as e:
            return _error(' '.join(e.messages))
        prop.refresh_from_db()
        return success({'status': prop.status, 'review_state': prop.review_state,
                        'missing_approvals': approvals.missing_approvals(prop)
                        if prop.review_state != Property.ReviewState.APPROVED else []},
                       message=f"Property {action} recorded.")


class _SubmitterActionView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    service = None

    def _can_act(self, user, prop):
        from apps.agencies.permissions import user_can_access_property
        return (user.role == 'admin' or user.is_staff or prop.submitted_by_id == user.id
                or (prop.landlord_id == user.id and not prop.requires_landlord_approval)
                or user_can_access_property(user, prop, required_permission='property.manage'))

    def post(self, request, id):
        prop = generics.get_object_or_404(Property, id=id)
        if not approvals.can_view_property(request.user, prop):
            raise NotFound('Property not found.')
        if not self._can_act(request.user, prop):
            raise PermissionDenied('You cannot act on this submission.')
        try:
            type(self).service(prop, request.user, request.data.get('comment', ''))
        except DjangoValidationError as e:
            return _error(' '.join(e.messages))
        prop.refresh_from_db()
        return success({'status': prop.status, 'review_state': prop.review_state})


class PropertyResubmitView(_SubmitterActionView):
    service = staticmethod(approvals.resubmit)


class PropertyWithdrawView(_SubmitterActionView):
    service = staticmethod(approvals.withdraw)


class PropertyApprovalHistoryView(generics.ListAPIView):
    """Immutable decision trail for one property (owner, submitter, managing agency, admin)."""
    serializer_class = PropertyApprovalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        prop = generics.get_object_or_404(Property, id=self.kwargs['id'])
        user = self.request.user
        from apps.agencies.permissions import user_can_access_property
        allowed = (user.role == 'admin' or user.is_staff or prop.landlord_id == user.id
                   or prop.submitted_by_id == user.id
                   or user_can_access_property(user, prop, required_permission='property.manage'))
        if not allowed:
            raise NotFound('Property not found.')
        return prop.approvals.select_related('actor')


class PropertyReviewQueueView(APIView):
    """
    Work queue. Admin: every property still waiting on an admin decision (oldest first,
    with age for bottleneck tracking). Landlord: their own properties waiting on them.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from django.utils import timezone
        user = request.user
        S = Property.ReviewState
        qs = Property.objects.filter(
            review_state__in=[S.AWAITING_LANDLORD, S.AWAITING_ADMIN]
        ).select_related('landlord', 'submitted_by_agency')
        if user.role == 'admin' or user.is_staff:
            role = 'admin'
            items = [p for p in qs if P_ADMIN in approvals.missing_approvals(p)]
        else:
            role = 'landlord'
            items = [p for p in qs.filter(landlord=user) if P_LANDLORD in approvals.missing_approvals(p)]
        now = timezone.now()
        rows = [{
            'id': str(p.id), 'name': p.name, 'town': p.town, 'county': p.county,
            'landlord_name': p.landlord.get_full_name(),
            'submitted_by_agency': p.submitted_by_agency.name if p.submitted_by_agency_id else None,
            'review_state': p.review_state, 'submission_version': p.submission_version,
            'requires_landlord_approval': p.requires_landlord_approval,
            'missing_approvals': approvals.missing_approvals(p),
            'age_days': (now - p.updated_at).days, 'submitted_at': p.created_at,
        } for p in items]
        rows.sort(key=lambda r: r['age_days'], reverse=True)
        return success({'role': role, 'count': len(rows), 'results': rows})


P_ADMIN = PropertyApproval.Party.ADMIN
P_LANDLORD = PropertyApproval.Party.LANDLORD


class UnitListCreateView(generics.ListCreateAPIView):
    serializer_class = UnitSerializer
    filterset_fields = ['status', 'bedrooms']

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        prop = generics.get_object_or_404(Property, id=self.kwargs['property_id'])
        _visible_property_or_404(self.request.user, prop)
        return Unit.objects.filter(property=prop)

    def perform_create(self, serializer):
        from apps.agencies.permissions import user_can_access_property
        prop = generics.get_object_or_404(Property, id=self.kwargs['property_id'])
        user = self.request.user
        if not (user.role == 'admin' or user.is_staff or approvals.is_agent_submitter(user, prop)
                or user_can_access_property(user, prop, required_permission='property.manage')):
            raise PermissionDenied("You do not have permission to manage this property.")
        serializer.save(property_id=self.kwargs['property_id'])


class UnitDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UnitSerializer
    queryset = Unit.objects.all()
    lookup_field = 'id'

    def get_object(self):
        obj = super().get_object()
        if self.request.method == 'GET':
            _visible_property_or_404(self.request.user, obj.property)
        return obj

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def _check_can_manage(self, request, instance):
        from apps.agencies.permissions import user_can_access_property
        if request.user.role == 'admin' or request.user.is_staff:
            return
        if approvals.is_agent_submitter(request.user, instance.property):
            return
        if not user_can_access_property(request.user, instance.property, required_permission='property.manage'):
            raise PermissionDenied("You do not have permission to manage this property.")

    def update(self, request, *args, **kwargs):
        self._check_can_manage(request, self.get_object())
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        self._check_can_manage(request, self.get_object())
        return super().destroy(request, *args, **kwargs)


class SavedPropertyListView(generics.ListCreateAPIView):
    serializer_class = SavedPropertySerializer

    def get_queryset(self):
        return SavedProperty.objects.filter(user=self.request.user)


class SavedPropertyDeleteView(generics.DestroyAPIView):
    queryset = SavedProperty.objects.all()

    def get_object(self):
        return SavedProperty.objects.get(user=self.request.user, property_id=self.kwargs['property_id'])


class PropertyReviewListCreateView(generics.ListCreateAPIView):
    serializer_class = PropertyReviewSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        prop = generics.get_object_or_404(Property, id=self.kwargs['property_id'])
        _visible_property_or_404(self.request.user, prop)
        return PropertyReview.objects.filter(property=prop)

    def perform_create(self, serializer):
        prop = generics.get_object_or_404(Property, id=self.kwargs['property_id'])
        _visible_property_or_404(self.request.user, prop)
        serializer.save(reviewer=self.request.user, property=prop)


class PropertyDocumentListCreateView(generics.ListCreateAPIView):
    """
    Secure document vault. The owning landlord, admins, and agency staff with
    property.manage rights on the property can list or upload - these are title deeds
    and compliance certificates, not public listing content. By default only the
    current version of each document type is shown; pass ?all_versions=true to see
    the full history.
    """
    serializer_class = PropertyDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['document_type']

    def _can_access(self, user, prop):
        from apps.agencies.permissions import user_can_access_property
        return (
            user.role == 'admin' or user.is_staff
            or user_can_access_property(user, prop, required_permission='property.manage')
        )

    def get_queryset(self):
        prop = generics.get_object_or_404(Property, id=self.kwargs['property_id'])
        if not self._can_access(self.request.user, prop):
            return PropertyDocument.objects.none()

        qs = PropertyDocument.objects.filter(property=prop).select_related('uploaded_by')
        if self.request.query_params.get('all_versions', '').lower() != 'true':
            qs = qs.filter(is_current=True)
        return qs.order_by('document_type', '-version')

    def perform_create(self, serializer):
        prop = generics.get_object_or_404(Property, id=self.kwargs['property_id'])
        if not self._can_access(self.request.user, prop):
            raise PermissionDenied("You can only upload documents for properties you own or manage.")
        serializer.save(property=prop)


class PropertyDocumentDetailView(generics.RetrieveDestroyAPIView):
    """Download/delete a single document version. Same ownership/management restriction as the list view."""
    serializer_class = PropertyDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = PropertyDocument.objects.all()
    lookup_field = 'id'

    def get_object(self):
        obj = super().get_object()
        from apps.agencies.permissions import user_can_access_property
        user = self.request.user
        if not (user.role == 'admin' or user.is_staff
                or user_can_access_property(user, obj.property, required_permission='property.manage')):
            raise PermissionDenied("You do not have access to this document.")
        return obj


class UnitCostOfLivingView(APIView):
    """
    Total Cost of Living Comparison - from the FRIDAH 2.0 market-trends/product
    plan (2026): "compare rent plus service charge, utilities, internet,
    estimated transport and other recurring costs so tenants can compare true
    monthly affordability."

    Returns the platform's real, grounded figures only (rent + known utility
    costs on this unit) - it does NOT estimate transport, internet-if-untracked,
    or other personal costs, since FRIDAH has no reliable data source for those.
    The client is expected to let the tenant add their own estimates for those
    categories and sum them client-side; we don't persist personal what-if
    numbers server-side, since they aren't platform data.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, id):
        from decimal import Decimal
        from django.db.models import Avg
        from apps.rentals.models import UtilityAccount, Invoice

        unit = generics.get_object_or_404(Unit, id=id)
        _visible_property_or_404(request.user, unit.property)
        utility_lines = []
        utilities_total = Decimal('0')

        for account in UtilityAccount.objects.filter(unit=unit, is_active=True):
            if not account.is_metered and account.flat_monthly_fee is not None:
                utility_lines.append({
                    'utility_type': account.utility_type,
                    'monthly_estimate': str(account.flat_monthly_fee),
                    'basis': 'flat_fee',
                })
                utilities_total += account.flat_monthly_fee
                continue

            # Metered (water/electricity): no fixed monthly figure exists, so estimate
            # from this unit's own recent utility invoice history across whichever
            # leases have lived there - a real, unit-specific average rather than a
            # guessed platform-wide constant.
            avg = Invoice.objects.filter(
                lease__unit=unit, invoice_type=Invoice.InvoiceType.UTILITY,
            ).order_by('-created_at')[:6].aggregate(avg=Avg('amount'))['avg']
            if avg:
                utility_lines.append({
                    'utility_type': account.utility_type,
                    'monthly_estimate': str(Decimal(avg).quantize(Decimal('0.01'))),
                    'basis': 'historical_average',
                })
                utilities_total += Decimal(avg)
            else:
                utility_lines.append({
                    'utility_type': account.utility_type, 'monthly_estimate': None,
                    'basis': 'no_data',
                })

        return success({
            'unit_id': str(unit.id),
            'rent': str(unit.rent_amount),
            'utilities': utility_lines,
            'platform_total': str((unit.rent_amount + utilities_total).quantize(Decimal('0.01'))),
            'note': (
                'This total includes rent and known utility costs only. Transport, '
                'internet (if not separately metered here), and other personal costs '
                "are not platform data - add your own estimates in the app to get a "
                'complete monthly total.'
            ),
        })


class PropertyRecommendationsView(APIView):
    """Rule-based recommendations - see apps/properties/recommendations.py for
    the scoring approach and why it's deliberately not AI-based."""

    def get(self, request):
        from .recommendations import get_recommendations
        limit = min(int(request.query_params.get('limit', 10)), 30)
        results, is_personalized = get_recommendations(request.user, limit=limit)
        return success({
            'is_personalized': is_personalized,
            'results': [
                {
                    'property': PropertyListSerializer(r['property'], context={'request': request}).data,
                    'score': r['score'],
                    'reasons': r['reasons'],
                }
                for r in results
            ],
        })
