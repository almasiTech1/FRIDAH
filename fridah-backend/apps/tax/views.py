import csv
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q, Sum, Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.agencies.models import OwnerStatement
from apps.agencies.permissions import agency_membership_for
from apps.users.permissions import IsAdminRole
from . import services
from .models import TaxType, TaxRule, TaxRecord
from .serializers import TaxTypeSerializer, TaxRuleSerializer, TaxRecordSerializer, TaxAdjustmentSerializer


def _ok(data=None, message='OK', status=200):
    return Response({'success': True, 'message': message, 'data': data}, status=status)


def _err(message, status=400):
    return Response({'success': False, 'error': {'message': message}}, status=status)


def _is_admin(user):
    return user.role == 'admin' or user.is_staff


def tax_records_visible_to(user):
    """Owner sees own records; admin all; agency finance staff the records of their agency's statements."""
    if _is_admin(user):
        return TaxRecord.objects.all()
    q = Q(owner=user)
    membership = agency_membership_for(user)
    if membership and membership.has_permission('statements.issue'):
        q |= Q(statement__agency=membership.agency)
    return TaxRecord.objects.filter(q).distinct()


def statements_visible_to(user):
    if _is_admin(user):
        return OwnerStatement.objects.all()
    released = (OwnerStatement.Status.ISSUED, OwnerStatement.Status.PAID)
    q = Q(owner=user, status__in=released)
    membership = agency_membership_for(user)
    if membership:
        q |= Q(agency=membership.agency)
    return OwnerStatement.objects.filter(q)


class TaxTypeListCreateView(generics.ListCreateAPIView):
    serializer_class = TaxTypeSerializer
    queryset = TaxType.objects.all()

    def get_permissions(self):
        return [IsAdminRole()] if self.request.method == 'POST' else [permissions.IsAuthenticated()]


class TaxRuleListCreateView(generics.ListCreateAPIView):
    """Rules are versioned: creating a rule never alters an earlier one, so past figures stay reproducible."""
    serializer_class = TaxRuleSerializer
    filterset_fields = ['tax_type', 'is_active']

    def get_permissions(self):
        return [IsAdminRole()] if self.request.method == 'POST' else [permissions.IsAuthenticated()]

    def get_queryset(self):
        return TaxRule.objects.select_related('tax_type')

    def perform_create(self, serializer):
        tax_type = serializer.validated_data['tax_type']
        last = TaxRule.objects.filter(tax_type=tax_type).order_by('-version').first()
        serializer.save(version=(last.version + 1) if last else 1, created_by=self.request.user)


class TaxRecordListView(generics.ListAPIView):
    serializer_class = TaxRecordSerializer
    filterset_fields = ['property', 'tax_type', 'status']

    def get_queryset(self):
        qs = tax_records_visible_to(self.request.user).select_related('tax_type', 'property', 'rule')
        year = self.request.query_params.get('year')
        if year and year.isdigit():
            qs = qs.filter(period_start__year=int(year))
        return qs


class TaxRecordDetailView(generics.RetrieveAPIView):
    serializer_class = TaxRecordSerializer
    lookup_field = 'id'

    def get_queryset(self):
        return tax_records_visible_to(self.request.user).select_related('tax_type', 'property', 'rule')


class TaxEstimateView(APIView):
    """POST {statement, tax_type: <code>, taxpayer_type?, withholding?} -> creates/refreshes an ESTIMATE."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        statement = statements_visible_to(request.user).filter(id=request.data.get('statement')).first()
        if statement is None:
            raise NotFound('Statement not found.')
        tax_type = get_object_or_404(TaxType, code=request.data.get('tax_type'), is_active=True)
        try:
            record = services.estimate_for_statement(
                statement, tax_type, taxpayer_type=request.data.get('taxpayer_type', 'individual'),
                withholding=Decimal(str(request.data.get('withholding', '0'))),
            )
        except DjangoValidationError as e:
            return _err(' '.join(e.messages))
        except ArithmeticError:
            return _err('Invalid amount.')
        return _ok(TaxRecordSerializer(record).data, 'Estimate saved.', 201)


class TaxRecordAdjustView(APIView):
    """
    Admin: correct any adjustable field. Owner: may only record a payment they made
    (amount_paid / reference / status=paid). Both require a reason and are audited.
    """
    permission_classes = [permissions.IsAuthenticated]
    OWNER_FIELDS = {'amount_paid', 'reference', 'status'}

    def post(self, request, id):
        record = tax_records_visible_to(request.user).filter(id=id).first()
        if record is None:
            raise NotFound('Tax record not found.')
        changes = {k: v for k, v in request.data.items() if k not in ('reason',)}
        if not _is_admin(request.user):
            if record.owner_id != request.user.id:
                raise PermissionDenied('Only the owner or an administrator can change a tax record.')
            if set(changes) - self.OWNER_FIELDS or changes.get('status', 'paid') not in ('paid', 'assessed'):
                raise PermissionDenied('Owners can only record a payment or an assessment reference.')
        try:
            record = services.adjust_record(record, request.user, request.data.get('reason', ''), **changes)
        except DjangoValidationError as e:
            return _err(' '.join(e.messages))
        return _ok(TaxRecordSerializer(record).data, 'Tax record updated.')


class TaxRecordAdjustmentsView(generics.ListAPIView):
    serializer_class = TaxAdjustmentSerializer

    def get_queryset(self):
        record = tax_records_visible_to(self.request.user).filter(id=self.kwargs['id']).first()
        if record is None:
            raise NotFound('Tax record not found.')
        return record.adjustments.select_related('actor')


def _summary_rows(qs):
    return list(
        qs.values('property_id', 'property__name', 'tax_type__code')
        .annotate(records=Count('id'), gross=Sum('gross_income'), expenses=Sum('allowable_expenses'),
                  calculated=Sum('calculated_amount'), withholding=Sum('withholding_credit'), paid=Sum('amount_paid'),
                  estimates=Count('id', filter=Q(status='estimated')))
        .order_by('property__name', 'tax_type__code')
    )


class TaxSummaryView(APIView):
    """Per-property / per-tax-type totals for a year, with a clear count of estimate-only records."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = tax_records_visible_to(request.user)
        year = request.query_params.get('year')
        if year and year.isdigit():
            qs = qs.filter(period_start__year=int(year))
        if request.query_params.get('property'):
            qs = qs.filter(property_id=request.query_params['property'])
        rows = _summary_rows(qs)
        zero = Decimal('0')
        out = []
        for r in rows:
            calc, wh, paid = r['calculated'] or zero, r['withholding'] or zero, r['paid'] or zero
            out.append({
                'property': str(r['property_id']) if r['property_id'] else None,
                'property_name': r['property__name'], 'tax_type': r['tax_type__code'], 'records': r['records'],
                'gross_income': r['gross'] or zero, 'allowable_expenses': r['expenses'] or zero,
                'calculated': calc, 'withholding_credit': wh, 'paid': paid,
                'balance_due': max(calc - wh - paid, zero), 'estimate_only_records': r['estimates'],
            })
        return _ok({'year': year, 'rows': out,
                    'notice': 'Figures marked estimate are not official KRA assessments.'})


class TaxExportView(APIView):
    """CSV export of the caller's (or admin's) tax records, to support filing and reconciliation."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = tax_records_visible_to(request.user).select_related('tax_type', 'property', 'rule')
        year = request.query_params.get('year')
        if year and year.isdigit():
            qs = qs.filter(period_start__year=int(year))
        resp = HttpResponse(content_type='text/csv')
        resp['Content-Disposition'] = f'attachment; filename="fridah-tax-records-{year or "all"}.csv"'
        w = csv.writer(resp)
        w.writerow(['Property', 'Tax type', 'Rule version', 'Period start', 'Period end', 'Gross income',
                    'Allowable expenses', 'Taxable base', 'Calculated', 'Withholding credit', 'Paid',
                    'Balance due', 'Status', 'Reference', 'Estimate?'])
        for r in qs:
            w.writerow([r.property.name if r.property else '', r.tax_type.code, r.rule.version if r.rule else '',
                        r.period_start, r.period_end, r.gross_income, r.allowable_expenses, r.taxable_base,
                        r.calculated_amount, r.withholding_credit, r.amount_paid, r.balance_due, r.status,
                        r.reference, 'ESTIMATE' if r.is_estimate else 'no'])
        return resp
