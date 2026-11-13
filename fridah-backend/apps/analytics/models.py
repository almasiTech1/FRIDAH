import uuid
from django.db import models
from django.conf import settings


class DashboardSnapshot(models.Model):
    """Optional daily-cached snapshot of computed metrics per user, to avoid heavy live aggregation."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dashboard_snapshots')
    snapshot_date = models.DateField()
    data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'dashboard_snapshots'
        unique_together = ('user', 'snapshot_date')


class PlatformMetric(models.Model):
    """Daily platform-wide metrics for admin analytics (revenue, active users, etc)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    metric_date = models.DateField(unique=True)
    total_users = models.PositiveIntegerField(default=0)
    total_properties = models.PositiveIntegerField(default=0)
    total_listings = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_commission = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    new_signups = models.PositiveIntegerField(default=0)
    active_leases = models.PositiveIntegerField(default=0)
    active_bookings = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'platform_metrics'


class TenantRiskScore(models.Model):
    """
    Cached 1-10 risk score for a tenant, computed from payment history, KYC status, and
    tenancy length. Recomputed nightly (and on-demand) rather than live per-request,
    since it's read frequently (landlords see it on every application).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='risk_score')

    score = models.PositiveSmallIntegerField(default=5)  # 1 = highest risk, 10 = lowest risk

    # Inputs kept alongside the score so landlords can see *why*, not just the number.
    on_time_payment_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # 0-100%
    total_invoices = models.PositiveIntegerField(default=0)
    overdue_invoices = models.PositiveIntegerField(default=0)
    is_kyc_verified = models.BooleanField(default=False)
    months_on_platform = models.PositiveIntegerField(default=0)
    completed_tenancies = models.PositiveIntegerField(default=0)
    has_blacklist_flags = models.BooleanField(default=False)

    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tenant_risk_scores'
        indexes = [models.Index(fields=['score'])]

    def __str__(self):
        return f"{self.tenant} - risk score {self.score}/10"
