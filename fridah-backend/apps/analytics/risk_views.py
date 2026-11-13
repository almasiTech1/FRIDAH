from rest_framework.views import APIView
from apps.users.views import success
from apps.users.permissions import IsLandlordOrAdmin
from apps.users.models import User
from django.shortcuts import get_object_or_404


def _serialize_risk_score(rs):
    return {
        'tenant_id': str(rs.tenant_id),
        'score': rs.score,
        'on_time_payment_rate': float(rs.on_time_payment_rate),
        'total_invoices': rs.total_invoices,
        'overdue_invoices': rs.overdue_invoices,
        'is_kyc_verified': rs.is_kyc_verified,
        'months_on_platform': rs.months_on_platform,
        'completed_tenancies': rs.completed_tenancies,
        'has_blacklist_flags': rs.has_blacklist_flags,
        'computed_at': rs.computed_at,
    }


class TenantRiskScoreView(APIView):
    """
    Landlords view a tenant's risk score - shown on rental applications so landlords
    can make an informed decision before accepting a new tenant.
    """
    permission_classes = [IsLandlordOrAdmin]

    def get(self, request, tenant_id):
        from .models import TenantRiskScore
        from .services import calculate_tenant_risk_score

        tenant = get_object_or_404(User, id=tenant_id, role='tenant')
        risk_score = TenantRiskScore.objects.filter(tenant=tenant).first()
        if not risk_score:
            # No cached score yet (e.g. brand new tenant) - compute on demand rather
            # than making the landlord wait for the next nightly batch job.
            risk_score = calculate_tenant_risk_score(tenant)
        return success(_serialize_risk_score(risk_score))

    def post(self, request, tenant_id):
        """Force a recompute - useful right after a tenant's payment status changes."""
        from .services import calculate_tenant_risk_score
        tenant = get_object_or_404(User, id=tenant_id, role='tenant')
        risk_score = calculate_tenant_risk_score(tenant)
        return success(_serialize_risk_score(risk_score), message="Risk score recalculated.")
