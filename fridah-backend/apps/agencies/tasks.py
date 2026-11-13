"""
Scheduled owner statements (report section 3.6).

* Monthly statements: every day the task checks the PREVIOUS calendar month.
* Annual statements: during January the task also checks the PREVIOUS calendar year.

The task is idempotent: OwnerStatement has a unique (property, period_start, period_end)
constraint and generate_owner_statement() never touches a statement that has left DRAFT,
so running it daily (or twice) produces no duplicates and no duplicate notifications.

Release policy - money is involved, so a human stays in the loop where an agency manages
the property:
  * self-managed property  -> statement is generated and issued to the owner automatically
  * agency-managed property -> statement is generated as DRAFT for the agency to review and
                               issue (owners never see drafts); the agency is notified.
A failure on one property never stops the others; failures are logged and counted.
"""
import calendar
import logging
from datetime import date, timedelta

from celery import shared_task

logger = logging.getLogger(__name__)


def previous_month(today):
    first_of_this_month = today.replace(day=1)
    last_of_prev = first_of_this_month - timedelta(days=1)
    return last_of_prev.replace(day=1), last_of_prev


def previous_year(today):
    return date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)


def periods_due(today):
    due = [('monthly', *previous_month(today))]
    if today.month == 1:
        due.append(('annual', *previous_year(today)))
    return due


def _statement_exists(prop, start, end):
    from .models import OwnerStatement
    return OwnerStatement.objects.filter(property=prop, period_start=start, period_end=end).exists()


def generate_for_period(period_start, period_end, *, label='monthly'):
    from apps.properties.models import Property
    from . import services
    from .models import PropertyManagementAssignment

    summary = {'period': label, 'start': str(period_start), 'end': str(period_end),
               'generated': 0, 'issued': 0, 'left_for_agency_review': 0, 'skipped': 0, 'failed': 0}

    # Only published properties have ledgers worth reporting on.
    for prop in Property.objects.filter(status=Property.Status.ACTIVE).select_related('landlord').iterator():
        try:
            already = _statement_exists(prop, period_start, period_end)
            statement = services.generate_owner_statement(
                property=prop, period_start=period_start, period_end=period_end, generated_by=None,
            )
            if already:
                summary['skipped'] += 1
                continue
            summary['generated'] += 1
            if PropertyManagementAssignment.active_for_property(prop) is None:
                services.issue_statement(statement, issued_by=None)
                summary['issued'] += 1
            else:
                summary['left_for_agency_review'] += 1
                _notify_agency(statement)
        except Exception:
            summary['failed'] += 1
            logger.exception('Scheduled statement failed for property %s (%s - %s)', prop.id, period_start, period_end)
    logger.info('Scheduled owner statements: %s', summary)
    return summary


def _notify_agency(statement):
    try:
        from apps.notifications.services import notify_user
        from .models import AgencyMembership, AgencyRole
        if not statement.agency_id:
            return
        recipients = AgencyMembership.objects.filter(
            agency_id=statement.agency_id, status=AgencyMembership.Status.ACTIVE,
            role__role_type__in=[AgencyRole.RoleType.AGENCY_ADMIN, AgencyRole.RoleType.FINANCE_OFFICER],
        ).select_related('user')
        for m in recipients:
            notify_user(
                m.user, 'Owner statement ready for review',
                f'{statement.property.name}: statement for {statement.period_start} - {statement.period_end} '
                f'is ready to review and issue.', notification_type='payment', send_push=False,
            )
    except Exception:
        logger.exception('Failed to notify agency about draft statement')


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_backoff_max=900, max_retries=3)
def generate_scheduled_owner_statements(self, today_iso=None):
    """Celery entry point. `today_iso` lets operators re-run a specific day (admin re-run)."""
    today = date.fromisoformat(today_iso) if today_iso else date.today()
    return [generate_for_period(start, end, label=label) for label, start, end in periods_due(today)]
