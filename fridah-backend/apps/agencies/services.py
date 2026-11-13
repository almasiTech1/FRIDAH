import uuid
import logging
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import (
    Agency, AgencyRole, AgencyMembership, PropertyManagementAssignment, PropertyStaffAssignment,
    AgencyFeeRule, ManagementAgreement, OwnerStatement, OwnerPayout, AgencyCommission,
    AgencyExpense, AgencyAuditLog,
)

logger = logging.getLogger('apps.agencies')


def log_audit(agency, actor, action, target=None, changes=None, ip_address=None):
    AgencyAuditLog.objects.create(
        agency=agency, actor=actor, action=action,
        target_type=target.__class__.__name__ if target is not None else '',
        target_id=str(getattr(target, 'id', '')) if target is not None else '',
        changes=changes or {}, ip_address=ip_address,
    )


@transaction.atomic
def create_agency(*, name, created_by, **fields):
    """Create an agency, seed its standard roles, and make the creator its first Agency Admin."""
    agency = Agency.objects.create(name=name, created_by=created_by, **fields)
    roles = AgencyRole.seed_defaults(agency)
    admin_role = next(r for r in roles if r.role_type == AgencyRole.RoleType.AGENCY_ADMIN)
    membership = AgencyMembership.objects.create(
        agency=agency, user=created_by, role=admin_role,
        status=AgencyMembership.Status.ACTIVE, joined_at=timezone.now(),
    )
    log_audit(agency, created_by, 'agency.created', target=agency)
    log_audit(agency, created_by, 'staff.joined', target=membership, changes={'role': admin_role.role_type})
    return agency


def generate_temporary_password(length=12):
    """Random, easy-to-read-aloud password (no look-alike characters) for admin-issued accounts."""
    import secrets
    alphabet = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    while True:
        pw = ''.join(secrets.choice(alphabet) for _ in range(length))
        if any(c.islower() for c in pw) and any(c.isupper() for c in pw) and any(c.isdigit() for c in pw):
            return pw


def _unique_username(email):
    from apps.users.models import User
    base = (email.split('@')[0] or 'agency')[:20]
    candidate, n = base, 1
    while User.objects.filter(username=candidate).exists():
        n += 1
        candidate = f'{base}{n}'
    return candidate


@transaction.atomic
def register_agency(*, registered_by, admin_first_name, admin_last_name, admin_email, admin_phone_number, **fields):
    """
    Platform administrator registers an agency company AND the login for its first Agency Admin.

    Agencies are never self-registered: there is no public sign-up path to an agency, and the
    first Agency Admin's account is created here by the administrator. The account starts with a
    random temporary password (returned once to the administrator, never stored in clear) that must
    be changed at first login. The agency is active immediately because an administrator vetted it.

    Returns (agency, agency_admin_user, temporary_password).
    """
    from apps.users.models import User
    temp_password = generate_temporary_password()
    # Agency staff carry an ordinary base role (the platform has no separate 'agency' role);
    # what makes them agency staff is their AgencyMembership, exactly as for the demo agency account.
    agency_admin = User(
        username=_unique_username(admin_email), email=admin_email.lower().strip(),
        first_name=admin_first_name.strip(), last_name=admin_last_name.strip(),
        phone_number=admin_phone_number, role=User.Role.LANDLORD, is_active=True,
        must_change_password=True,
    )
    agency_admin.set_password(temp_password)
    agency_admin.save()

    agency = Agency.objects.create(created_by=registered_by, status=Agency.Status.ACTIVE, **fields)
    roles = AgencyRole.seed_defaults(agency)
    admin_role = next(r for r in roles if r.role_type == AgencyRole.RoleType.AGENCY_ADMIN)
    membership = AgencyMembership.objects.create(
        agency=agency, user=agency_admin, role=admin_role,
        status=AgencyMembership.Status.ACTIVE, joined_at=timezone.now(), invited_by=registered_by,
    )
    log_audit(agency, registered_by, 'agency.registered_by_admin', target=agency,
              changes={'agency_admin': str(agency_admin.id), 'agency_admin_email': agency_admin.email,
                       'account_created_by_admin': True})
    log_audit(agency, registered_by, 'staff.joined', target=membership, changes={'role': admin_role.role_type})
    return agency, agency_admin, temp_password


@transaction.atomic
def reset_agency_admin_password(*, agency, admin):
    """
    There is no self-service password reset for agency accounts, so an administrator can issue a
    new temporary password to the agency's Agency Admin. Returns (user, temporary_password).
    """
    membership = (AgencyMembership.objects.select_related('user')
                  .filter(agency=agency, role__role_type=AgencyRole.RoleType.AGENCY_ADMIN,
                          status=AgencyMembership.Status.ACTIVE).order_by('joined_at').first())
    if membership is None:
        raise ValueError('This agency has no active Agency Admin.')
    user = membership.user
    temp_password = generate_temporary_password()
    user.set_password(temp_password)
    user.must_change_password = True
    user.save(update_fields=['password', 'must_change_password'])
    log_audit(agency, admin, 'agency.admin_password_reset', target=membership, changes={'user': str(user.id)})
    return user, temp_password


@transaction.atomic
def set_agency_status(*, agency, admin, status):
    """Admin activates, suspends or archives an agency. Suspended/archived agencies leave the directory."""
    allowed = {Agency.Status.ACTIVE, Agency.Status.SUSPENDED, Agency.Status.ARCHIVED}
    if status not in allowed:
        raise ValueError('Invalid agency status.')
    old = agency.status
    agency.status = status
    agency.save(update_fields=['status', 'updated_at'])
    log_audit(agency, admin, 'agency.status_changed', target=agency, changes={'from': old, 'to': status})
    return agency


@transaction.atomic
def invite_staff(*, agency, invited_by, user, role):
    membership, created = AgencyMembership.objects.get_or_create(
        agency=agency, user=user,
        defaults={'role': role, 'status': AgencyMembership.Status.INVITED, 'invited_by': invited_by},
    )
    if not created:
        membership.role = role
        membership.status = AgencyMembership.Status.INVITED
        membership.invited_by = invited_by
        membership.save(update_fields=['role', 'status', 'invited_by'])
    log_audit(agency, invited_by, 'staff.invited', target=membership, changes={'role': role.name, 'user': str(user.id)})

    try:
        from apps.notifications.services import notify_user
        notify_user(
            user, title=f"Invited to {agency.name}",
            message=f"You've been invited to join {agency.name} as {role.name}. Accept in the app to get started.",
            notification_type='general',
        )
    except Exception:
        logger.exception("Failed to notify invited staff member")
    return membership


@transaction.atomic
def create_staff_account(*, agency, created_by, role, first_name, last_name, email, phone_number):
    """
    The agency creates the login for a new staff member - they never self-register. The account
    starts with a temporary password (returned once, to be handed over) that must be changed at
    first login, and the membership is active straight away because the agency itself created it.
    Returns (membership, temporary_password).
    """
    from apps.users.models import User
    temp_password = generate_temporary_password()
    user = User(
        username=_unique_username(email), email=email.lower().strip(), first_name=first_name.strip(),
        last_name=last_name.strip(), phone_number=phone_number, role=User.Role.LANDLORD, is_active=True,
        must_change_password=True,
    )
    user.set_password(temp_password)
    user.save()
    membership = AgencyMembership.objects.create(
        agency=agency, user=user, role=role, status=AgencyMembership.Status.ACTIVE,
        joined_at=timezone.now(), invited_by=created_by,
    )
    log_audit(agency, created_by, 'staff.account_created', target=membership,
              changes={'role': role.name, 'user': str(user.id), 'email': user.email})
    return membership, temp_password


@transaction.atomic
def reset_staff_password(*, membership, reset_by):
    """Issue a new temporary password to a staff member (there is no self-service reset)."""
    user = membership.user
    temp_password = generate_temporary_password()
    user.set_password(temp_password)
    user.must_change_password = True
    user.save(update_fields=['password', 'must_change_password'])
    log_audit(membership.agency, reset_by, 'staff.password_reset', target=membership, changes={'user': str(user.id)})
    return temp_password


def accept_invite(membership):
    membership.status = AgencyMembership.Status.ACTIVE
    membership.joined_at = timezone.now()
    membership.save(update_fields=['status', 'joined_at'])
    log_audit(membership.agency, membership.user, 'staff.accepted', target=membership)
    return membership


@transaction.atomic
def assign_property_to_agency(
    *, property, agency, start_date, management_fee_percent=None, payout_rule=None,
    approved_by=None, fee_rule=None, agreement=None,
):
    """
    Ends any currently-active management assignment for the property (preserving it as
    history) and creates a new one. Only one assignment may be ACTIVE per property.
    """
    existing = PropertyManagementAssignment.active_for_property(property)
    if existing:
        existing.end(reason=f"Superseded by new assignment to {agency.name}", by_user=approved_by)

    assignment = PropertyManagementAssignment.objects.create(
        property=property, agency=agency, agreement=agreement, fee_rule=fee_rule,
        management_fee_percent=management_fee_percent if management_fee_percent is not None else agency.default_fee_percent,
        payout_rule=payout_rule or PropertyManagementAssignment.PayoutRule.OWNER_DIRECT,
        start_date=start_date, approved_by=approved_by,
    )
    log_audit(
        agency, approved_by, 'assignment.created', target=assignment,
        changes={'property': str(property.id), 'fee_percent': str(assignment.management_fee_percent)},
    )
    return assignment


def assign_listing_to_agency(
    *, listing, agency, start_date, management_fee_percent=None, payout_rule=None,
    approved_by=None, fee_rule=None, agreement=None,
):
    """The short-stay/hotel equivalent of assign_property_to_agency() - same rules, one
    active assignment per listing, prior assignment preserved as ended history."""
    existing = PropertyManagementAssignment.active_for_listing(listing)
    if existing:
        existing.end(reason=f"Superseded by new assignment to {agency.name}", by_user=approved_by)

    assignment = PropertyManagementAssignment.objects.create(
        listing=listing, agency=agency, agreement=agreement, fee_rule=fee_rule,
        management_fee_percent=management_fee_percent if management_fee_percent is not None else agency.default_fee_percent,
        payout_rule=payout_rule or PropertyManagementAssignment.PayoutRule.OWNER_DIRECT,
        start_date=start_date, approved_by=approved_by,
    )
    log_audit(
        agency, approved_by, 'assignment.created', target=assignment,
        changes={'listing': str(listing.id), 'fee_percent': str(assignment.management_fee_percent)},
    )
    return assignment


def end_assignment(assignment, *, reason='', by_user=None):
    assignment.end(reason=reason, by_user=by_user)
    log_audit(assignment.agency, by_user, 'assignment.ended', target=assignment, changes={'reason': reason})
    return assignment


@transaction.atomic
def assign_staff_to_property(*, property, membership, assigned_by=None):
    staff_assignment, created = PropertyStaffAssignment.objects.get_or_create(
        property=property, membership=membership, defaults={'is_active': True}
    )
    if not created and not staff_assignment.is_active:
        staff_assignment.is_active = True
        staff_assignment.removed_at = None
        staff_assignment.save(update_fields=['is_active', 'removed_at'])
    log_audit(
        membership.agency, assigned_by, 'staff.assigned_property', target=staff_assignment,
        changes={'property': str(property.id), 'user': str(membership.user_id)},
    )
    return staff_assignment


def remove_staff_from_property(staff_assignment, *, removed_by=None):
    staff_assignment.is_active = False
    staff_assignment.removed_at = timezone.now()
    staff_assignment.save(update_fields=['is_active', 'removed_at'])
    log_audit(
        staff_assignment.membership.agency, removed_by, 'staff.removed_property', target=staff_assignment,
    )
    return staff_assignment


def _collected_rent_for_period(property, period_start, period_end):
    from common.calculations import collected_rent_for_period
    return collected_rent_for_period(property, period_start, period_end)


def _arrears_for_period(property, period_end):
    from common.calculations import arrears_for_property
    return arrears_for_property(property, period_end)


def _vacancy_loss_for_period(property, period_start, period_end):
    from common.calculations import vacancy_loss_for_period
    return vacancy_loss_for_period(property, period_start, period_end)


@transaction.atomic
def generate_owner_statement(*, property, period_start, period_end, generated_by=None):
    """
    Builds (or refreshes, if still DRAFT) the owner statement for a property/period:
    gross rent collected, vacancy loss, arrears, agency commission, approved expenses,
    other deductions, and the resulting net payable.
    """
    assignment = PropertyManagementAssignment.active_for_property(property)
    agency = assignment.agency if assignment else None
    owner = property.landlord

    statement, created = OwnerStatement.objects.get_or_create(
        property=property, period_start=period_start, period_end=period_end,
        defaults={'agency': agency, 'owner': owner, 'generated_by': generated_by},
    )
    if not created and statement.status != OwnerStatement.Status.DRAFT:
        return statement  # issued/paid statements are immutable

    gross = _collected_rent_for_period(property, period_start, period_end)
    vacancy = _vacancy_loss_for_period(property, period_start, period_end)
    arrears = _arrears_for_period(property, period_end)

    commission = Decimal('0')
    if assignment:
        fee_rule = assignment.fee_rule
        if fee_rule:
            commission = fee_rule.compute_fee(gross)
        else:
            commission = (gross * assignment.management_fee_percent / 100).quantize(Decimal('0.01'))

    expenses_qs = AgencyExpense.objects.filter(
        property=property, incurred_on__gte=period_start, incurred_on__lte=period_end,
        is_deductible_from_owner=True,
    )
    expenses_total = expenses_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')

    statement.agency = agency
    statement.owner = owner
    statement.gross_rent_collected = gross
    statement.vacancy_loss = vacancy
    statement.arrears = arrears
    statement.agency_commission = commission
    statement.approved_expenses = expenses_total
    statement.other_deductions = statement.other_deductions or Decimal('0')
    statement.recompute_net()
    statement.generated_by = generated_by
    statement.save()

    expenses_qs.update(statement=statement)

    if assignment and commission:
        AgencyCommission.objects.update_or_create(
            agency=assignment.agency, property=property, period_start=period_start, period_end=period_end,
            defaults={
                'assignment': assignment, 'statement': statement, 'gross_amount': gross,
                'commission_rate': assignment.management_fee_percent, 'commission_amount': commission,
            },
        )

    if agency:
        log_audit(
            agency, generated_by, 'statement.generated', target=statement,
            changes={'gross': str(gross), 'commission': str(commission), 'net': str(statement.net_payable)},
        )
    return statement


@transaction.atomic
def generate_owner_statement_for_listing(*, listing, period_start, period_end, generated_by=None):
    """
    The short-stay/hotel equivalent of generate_owner_statement(): gross revenue from
    checked-out bookings, agency commission, and the resulting net payable. Vacancy loss
    and arrears are rental-specific concepts and stay at zero here - occupancy for the
    period is available separately via common.calculations.occupancy_for_period() for
    display, rather than folded into this statement's ledger figures.
    """
    from common.calculations import collected_booking_revenue_for_period

    assignment = PropertyManagementAssignment.active_for_listing(listing)
    agency = assignment.agency if assignment else None
    owner = listing.host

    statement, created = OwnerStatement.objects.get_or_create(
        listing=listing, period_start=period_start, period_end=period_end,
        defaults={'agency': agency, 'owner': owner, 'generated_by': generated_by},
    )
    if not created and statement.status != OwnerStatement.Status.DRAFT:
        return statement  # issued/paid statements are immutable

    gross = collected_booking_revenue_for_period(listing, period_start, period_end)

    commission = Decimal('0')
    if assignment:
        fee_rule = assignment.fee_rule
        if fee_rule:
            commission = fee_rule.compute_fee(gross)
        else:
            commission = (gross * assignment.management_fee_percent / 100).quantize(Decimal('0.01'))

    statement.agency = agency
    statement.owner = owner
    statement.gross_rent_collected = gross
    statement.vacancy_loss = Decimal('0')
    statement.arrears = Decimal('0')
    statement.agency_commission = commission
    statement.approved_expenses = statement.approved_expenses or Decimal('0')
    statement.other_deductions = statement.other_deductions or Decimal('0')
    statement.recompute_net()
    statement.generated_by = generated_by
    statement.save()

    if assignment and commission:
        AgencyCommission.objects.update_or_create(
            agency=assignment.agency, listing=listing, period_start=period_start, period_end=period_end,
            defaults={
                'assignment': assignment, 'statement': statement, 'gross_amount': gross,
                'commission_rate': assignment.management_fee_percent, 'commission_amount': commission,
            },
        )

    if agency:
        log_audit(
            agency, generated_by, 'statement.generated', target=statement,
            changes={'gross': str(gross), 'commission': str(commission), 'net': str(statement.net_payable)},
        )
    return statement


@transaction.atomic
def issue_statement(statement, *, issued_by=None):
    statement.status = OwnerStatement.Status.ISSUED
    statement.issued_at = timezone.now()
    statement.save(update_fields=['status', 'issued_at'])
    if statement.agency:
        log_audit(statement.agency, issued_by, 'statement.issued', target=statement)

    try:
        from apps.notifications.services import notify_user
        item_name = statement.property.name if statement.property_id else statement.listing.name
        notify_user(
            statement.owner, title="Owner Statement Ready",
            message=(
                f"Your statement for {item_name} "
                f"({statement.period_start} - {statement.period_end}) is ready. "
                f"Net payable: KES {statement.net_payable:,.2f}."
            ),
            notification_type='payment', send_sms_too=True,
        )
    except Exception:
        logger.exception("Failed to notify owner of issued statement")
    return statement


@transaction.atomic
def execute_owner_payout(statement, *, initiated_by=None, phone_number=''):
    """Creates and (best-effort) triggers an M-Pesa B2C payout of a statement's net payable to its owner."""
    if statement.net_payable <= 0:
        raise ValueError("Net payable must be greater than zero to execute a payout.")

    payout = OwnerPayout.objects.create(
        statement=statement, owner=statement.owner, amount=statement.net_payable,
        phone_number=phone_number or getattr(statement.owner, 'phone_number', ''),
        initiated_by=initiated_by,
    )
    if statement.agency:
        log_audit(statement.agency, initiated_by, 'payout.initiated', target=payout, changes={'amount': str(payout.amount)})

    try:
        from apps.payments.mpesa_client import MpesaClient
        client = MpesaClient()
        item_name = statement.property.name if statement.property_id else statement.listing.name
        result = client.b2c_payment(
            phone_number=payout.phone_number, amount=payout.amount,
            remarks=f"FRIDAH owner payout {item_name}",
            occasion=payout.reference,
        )
        payout.status = OwnerPayout.Status.PROCESSING
        payout.transaction_id = result.get('ConversationID', '')
        payout.save(update_fields=['status', 'transaction_id'])
    except Exception as e:
        logger.warning("Owner payout B2C dispatch failed, left pending for manual processing: %s", e)

    return payout


def mark_payout_completed(payout, raw_callback=None):
    payout.status = OwnerPayout.Status.COMPLETED
    payout.completed_at = timezone.now()
    payout.raw_callback = raw_callback or {}
    payout.save(update_fields=['status', 'completed_at', 'raw_callback'])
    payout.statement.status = OwnerStatement.Status.PAID
    payout.statement.save(update_fields=['status'])
    if payout.statement.agency:
        log_audit(payout.statement.agency, None, 'payout.completed', target=payout)
    return payout


def mark_payout_failed(payout, reason='', raw_callback=None):
    payout.status = OwnerPayout.Status.FAILED
    payout.raw_callback = raw_callback or {'reason': reason}
    payout.save(update_fields=['status', 'raw_callback'])
    if payout.statement.agency:
        log_audit(payout.statement.agency, None, 'payout.failed', target=payout, changes={'reason': reason})
    return payout
