import logging
from decimal import Decimal
from django.utils import timezone

logger = logging.getLogger('apps.analytics')


def calculate_tenant_risk_score(tenant):
    """
    Computes a 1-10 risk score for a tenant (10 = lowest risk / most trustworthy) from:
      - on-time payment rate on their invoices (heaviest weight)
      - active platform-wide blacklist flags (large penalty - this is what landlords
        care about most before accepting a new tenant)
      - KYC verification status
      - tenancy length / completed tenancies (longer good history = lower risk)

    Returns the updated/created TenantRiskScore instance.
    """
    from .models import TenantRiskScore
    from apps.rentals.models import Invoice, Lease
    from apps.users.models import TenantBlacklistEntry

    invoices = Invoice.objects.filter(tenant=tenant)
    total_invoices = invoices.count()
    paid_invoices = invoices.filter(status=Invoice.Status.PAID)
    overdue_invoices = invoices.filter(status=Invoice.Status.OVERDUE).count()

    # An invoice paid on or before its due date counts as "on time". Invoices with no
    # payment record yet (still pending, not yet due) are excluded from the rate entirely
    # rather than counted against the tenant.
    on_time_count = 0
    considered_count = 0
    for inv in paid_invoices.prefetch_related('payments'):
        last_payment = inv.payments.filter(completed_at__isnull=False).order_by('-completed_at').first()
        if not last_payment:
            continue
        considered_count += 1
        if last_payment.completed_at.date() <= inv.due_date:
            on_time_count += 1
    on_time_rate = Decimal(on_time_count) / Decimal(considered_count) * 100 if considered_count else Decimal('100')

    leases = Lease.objects.filter(tenant=tenant)
    completed_tenancies = leases.filter(status=Lease.Status.EXPIRED).count()
    first_lease = leases.order_by('start_date').first()
    months_on_platform = 0
    if first_lease:
        delta = timezone.now().date() - first_lease.start_date
        months_on_platform = max(delta.days // 30, 0)

    active_flags = TenantBlacklistEntry.objects.filter(
        tenant=tenant, status=TenantBlacklistEntry.Status.ACTIVE
    ).count()

    # Start at a neutral 5 and adjust. Deliberately weighted so a single active
    # blacklist flag or a poor payment record dominates the score, since those are
    # exactly the signals landlords are trying to surface.
    score = Decimal('5.0')
    score += (on_time_rate - Decimal('50')) / Decimal('12.5')  # +/-4 max, scaled around 50%
    score -= Decimal(min(overdue_invoices, 3))                 # -1 per overdue invoice, capped
    score -= Decimal(active_flags) * Decimal('2.5')            # heavy penalty per active flag
    score += Decimal('1') if tenant.kyc_status == 'verified' else Decimal('0')
    score += Decimal(min(completed_tenancies, 2)) * Decimal('0.5')
    score += Decimal('0.5') if months_on_platform >= 12 else Decimal('0')

    score = max(1, min(10, round(score)))

    risk_score, _ = TenantRiskScore.objects.update_or_create(
        tenant=tenant,
        defaults=dict(
            score=score,
            on_time_payment_rate=round(on_time_rate, 2),
            total_invoices=total_invoices,
            overdue_invoices=overdue_invoices,
            is_kyc_verified=(tenant.kyc_status == 'verified'),
            months_on_platform=months_on_platform,
            completed_tenancies=completed_tenancies,
            has_blacklist_flags=active_flags > 0,
        ),
    )
    return risk_score


def recalculate_all_tenant_risk_scores():
    from apps.users.models import User

    count = 0
    for tenant in User.objects.filter(role='tenant'):
        calculate_tenant_risk_score(tenant)
        count += 1
    logger.info("Recalculated risk scores for %d tenants.", count)
    return count
