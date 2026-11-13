import logging
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from .models import TaxRecord, TaxRule, TaxAdjustment

logger = logging.getLogger(__name__)
TWO = Decimal('0.01')
ESTIMATE_LABEL = 'ESTIMATE ONLY - not an official KRA assessment. Confirm with a qualified tax adviser.'


def _q(value):
    return Decimal(value).quantize(TWO, rounding=ROUND_HALF_UP)


def rule_for(tax_type, on_date, taxpayer_type='individual'):
    """The rule version in force on `on_date` (effective-dated). None when nothing is configured."""
    return (
        TaxRule.objects.filter(tax_type=tax_type, is_active=True, effective_from__lte=on_date)
        .filter(Q(effective_to__isnull=True) | Q(effective_to__gte=on_date))
        .filter(taxpayer_type__in=['any', taxpayer_type])
        .order_by('-effective_from', '-version').first()
    )


def compute(rule, gross, expenses=Decimal('0'), withholding=Decimal('0')):
    """Pure calculation returning the amount and a step-by-step, reproducible breakdown."""
    gross, expenses, withholding = _q(gross), _q(expenses), _q(withholding)
    steps = [f'Gross income: {gross}', f'Allowable expenses: {expenses}']
    if rule.method == TaxRule.Method.PERCENT_OF_NET:
        base = max(gross - expenses, Decimal('0'))
        steps.append(f'Taxable base (gross - expenses, floored at 0): {base}')
    else:
        base = gross
        steps.append(f'Taxable base (gross): {base}')

    if base <= rule.annual_threshold:
        amount = Decimal('0')
        steps.append(f'Base {base} is at or below threshold {rule.annual_threshold}: no tax')
    elif rule.method == TaxRule.Method.FLAT:
        amount = _q(rule.flat_amount)
        steps.append(f'Flat amount: {amount}')
    else:
        amount = _q(base * rule.rate / 100)
        steps.append(f'{base} x {rule.rate}% = {amount}')

    return {
        'taxable_base': base, 'calculated_amount': amount,
        'breakdown': {
            'label': ESTIMATE_LABEL, 'steps': steps,
            'rule': {'id': str(rule.id), 'tax_type': rule.tax_type.code, 'version': rule.version,
                     'method': rule.method, 'rate': str(rule.rate), 'flat_amount': str(rule.flat_amount),
                     'threshold': str(rule.annual_threshold), 'effective_from': str(rule.effective_from),
                     'professionally_reviewed': rule.is_professionally_reviewed},
            'withholding_credit': str(withholding),
        },
    }


@transaction.atomic
def estimate_for_statement(statement, tax_type, *, taxpayer_type='individual', withholding=Decimal('0')):
    """
    Create/refresh the ESTIMATE for one owner statement period. Assessed or paid records are
    never overwritten by a re-estimate - they can only change through adjust_record().
    """
    if not statement.property_id:
        raise ValidationError('Tax estimates are supported for rental property statements only.')
    rule = rule_for(tax_type, statement.period_end, taxpayer_type)
    if rule is None:
        raise ValidationError(
            f'No active {tax_type.name} rule is configured for {statement.period_end}. '
            'Ask an administrator to configure it (with professional review).'
        )
    gross = statement.gross_rent_collected
    expenses = statement.approved_expenses + statement.agency_commission
    result = compute(rule, gross, expenses, withholding)

    record, created = TaxRecord.objects.select_for_update().get_or_create(
        owner=statement.owner, property=statement.property, tax_type=tax_type,
        period_start=statement.period_start, period_end=statement.period_end,
        defaults={'rule': rule, 'statement': statement},
    )
    if not created and record.status != TaxRecord.Status.ESTIMATED:
        raise ValidationError('This record has been assessed or paid; use an authorised adjustment to change it.')
    record.rule, record.statement = rule, statement
    record.gross_income, record.allowable_expenses = _q(gross), _q(expenses)
    record.withholding_credit = _q(withholding)
    record.taxable_base = result['taxable_base']
    record.calculated_amount = result['calculated_amount']
    record.calculation_breakdown = result['breakdown']
    record.save()
    return record


_ADJUSTABLE = ('calculated_amount', 'amount_paid', 'withholding_credit', 'status', 'reference')


@transaction.atomic
def adjust_record(record, actor, reason, **changes):
    """Authorised correction. A reason is mandatory and the before/after is kept forever."""
    if not (reason or '').strip():
        raise ValidationError('A reason is required for every tax adjustment.')
    unknown = set(changes) - set(_ADJUSTABLE)
    if unknown:
        raise ValidationError(f'Fields cannot be adjusted: {", ".join(sorted(unknown))}')
    if 'status' in changes and changes['status'] not in TaxRecord.Status.values:
        raise ValidationError('Invalid status.')
    record = TaxRecord.objects.select_for_update().get(pk=record.pk)
    before = {f: str(getattr(record, f)) for f in _ADJUSTABLE}
    for field, value in changes.items():
        setattr(record, field, _q(value) if field in ('calculated_amount', 'amount_paid', 'withholding_credit') else value)
    record.save()
    after = {f: str(getattr(record, f)) for f in _ADJUSTABLE}
    TaxAdjustment.objects.create(record=record, actor=actor, reason=reason, before=before, after=after)
    try:
        from apps.audit.services import log_action
        log_action(actor=actor, action='tax.record.adjusted', target=record, property=record.property,
                   changes={'before': before, 'after': after, 'reason': reason[:500]}, severity='warning')
    except Exception:
        logger.exception('Failed to write platform audit log for tax adjustment')
    return record
