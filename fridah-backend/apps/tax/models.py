"""
Configurable, effective-dated tax recording (report section 3.7).

Deliberately contains NO hard-coded rates and no seeded rules: tax treatment depends on
taxpayer type, income type, thresholds, exemptions and current law, and must be configured
and validated by a qualified Kenyan tax adviser against current KRA guidance before use.
Everything computed here is an ESTIMATE until an official assessment/payment is recorded.
"""
import builtins
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models


class TaxType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.SlugField(max_length=40, unique=True)           # e.g. 'rental-income'
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tax_types'
        ordering = ['name']

    def __str__(self):
        return self.name


class TaxRule(models.Model):
    """
    One versioned rule for a tax type. Rules are never edited in place for their financial
    parameters - a rate change is a NEW rule with a new effective_from, so any past
    calculation can be reproduced from the rule version it used.
    """
    class Method(models.TextChoices):
        PERCENT_OF_GROSS = 'percent_of_gross', '% of gross income'
        PERCENT_OF_NET = 'percent_of_net', '% of income after allowable expenses'
        FLAT = 'flat', 'Flat amount per period'

    class TaxpayerType(models.TextChoices):
        ANY = 'any', 'Any'
        INDIVIDUAL = 'individual', 'Individual'
        COMPANY = 'company', 'Company'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tax_type = models.ForeignKey(TaxType, on_delete=models.PROTECT, related_name='rules')
    version = models.PositiveIntegerField(default=1)
    method = models.CharField(max_length=20, choices=Method.choices)
    rate = models.DecimalField(max_digits=7, decimal_places=4, default=0, help_text='Percent, e.g. 7.5 for 7.5%')
    flat_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    annual_threshold = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        help_text='Income at or below this (per period) attracts no tax under this rule.',
    )
    taxpayer_type = models.CharField(max_length=12, choices=TaxpayerType.choices, default=TaxpayerType.ANY)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    professional_reviewed_by = models.CharField(max_length=150, blank=True)
    professional_reviewed_on = models.DateField(null=True, blank=True)
    source_reference = models.CharField(max_length=255, blank=True, help_text='KRA guidance / Finance Act reference')
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tax_rules'
        ordering = ['tax_type', '-effective_from', '-version']
        unique_together = ('tax_type', 'version')

    @property
    def is_professionally_reviewed(self):
        return bool(self.professional_reviewed_by and self.professional_reviewed_on)

    def __str__(self):
        return f'{self.tax_type.code} v{self.version} from {self.effective_from}'


class TaxRecord(models.Model):
    class Status(models.TextChoices):
        ESTIMATED = 'estimated', 'Estimate (not an official assessment)'
        ASSESSED = 'assessed', 'Assessed'
        PAID = 'paid', 'Paid'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tax_records')
    property = models.ForeignKey('properties.Property', on_delete=models.CASCADE, null=True, blank=True,
                                 related_name='tax_records')
    tax_type = models.ForeignKey(TaxType, on_delete=models.PROTECT, related_name='records')
    rule = models.ForeignKey(TaxRule, on_delete=models.PROTECT, null=True, blank=True, related_name='records')
    statement = models.ForeignKey('agencies.OwnerStatement', on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='tax_records')

    period_start = models.DateField()
    period_end = models.DateField()

    gross_income = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    allowable_expenses = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    withholding_credit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    taxable_base = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    calculated_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ESTIMATED)
    reference = models.CharField(max_length=100, blank=True, help_text='KRA payment/assessment reference')
    calculation_breakdown = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tax_records'
        ordering = ['-period_start']
        indexes = [models.Index(fields=['owner', 'period_start']), models.Index(fields=['status'])]
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'property', 'tax_type', 'period_start', 'period_end'],
                name='unique_tax_record_period',
            ),
        ]

    @builtins.property
    def is_estimate(self):
        return self.status == self.Status.ESTIMATED

    @builtins.property
    def balance_due(self):
        return max(self.calculated_amount - self.withholding_credit - self.amount_paid, Decimal('0'))


class TaxAdjustment(models.Model):
    """Append-only history of every correction to a tax record, with the reason and the actor."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    record = models.ForeignKey(TaxRecord, on_delete=models.CASCADE, related_name='adjustments')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    reason = models.TextField()
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tax_adjustments'
        ordering = ['created_at']
