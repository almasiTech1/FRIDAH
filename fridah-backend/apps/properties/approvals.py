"""
Property approval workflow (dual approval for agent-submitted listings).

Rules enforced here, in the backend, inside transactions:

* A property is published (status == ACTIVE) only when every *required* party has an
  `approved` decision recorded against the property's CURRENT submission_version.
* Required parties: always the administrator; additionally the landlord when someone
  other than the owner (an agency) submitted the property.
* Landlord and admin may review in either order (parallel); publication needs both.
* A material edit bumps submission_version, which makes every earlier approval stale,
  unpublishes the listing and returns it to review.
* Every event is written to the immutable PropertyApproval trail and to the platform
  AuditLog.
"""
import logging

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from .models import Property, PropertyApproval

logger = logging.getLogger(__name__)

P = PropertyApproval.Party
D = PropertyApproval.Decision
S = Property.ReviewState

# What counts as a "material" edit is a product decision (report section 9); it is
# configurable via settings.PROPERTY_MATERIAL_FIELDS.
DEFAULT_MATERIAL_FIELDS = (
    'name', 'property_type', 'county', 'town', 'estate', 'address_detail',
    'latitude', 'longitude', 'total_units', 'description',
)


def material_fields():
    return tuple(getattr(settings, 'PROPERTY_MATERIAL_FIELDS', DEFAULT_MATERIAL_FIELDS))


# --------------------------------------------------------------------------- helpers
def _is_admin(user):
    return bool(user and user.is_authenticated and (user.role == 'admin' or user.is_staff))


def required_parties(prop):
    parties = [P.ADMIN]
    if prop.requires_landlord_approval:
        parties.insert(0, P.LANDLORD)
    return parties


def current_decisions(prop):
    """Latest approval-relevant decision per party for the CURRENT version only."""
    decisions = {}
    events = prop.approvals.filter(
        submission_version=prop.submission_version,
        party__in=[P.LANDLORD, P.ADMIN],
        decision__in=[D.APPROVED, D.REJECTED, D.CHANGES_REQUESTED],
    ).order_by('created_at')
    for ev in events:
        decisions[ev.party] = ev
    return decisions


def missing_approvals(prop):
    decided = current_decisions(prop)
    return [p for p in required_parties(prop) if p not in decided or decided[p].decision != D.APPROVED]


def _log(prop, party, decision, actor, comment='', from_state='', to_state='', **metadata):
    event = PropertyApproval.objects.create(
        property=prop, party=party, decision=decision, submission_version=prop.submission_version,
        actor=actor if (actor and actor.is_authenticated) else None,
        comment=comment or '', from_state=from_state, to_state=to_state, metadata=metadata,
    )
    try:
        from apps.audit.services import log_action
        log_action(
            actor=actor if (actor and actor.is_authenticated) else None,
            action=f'property.approval.{decision}', target=prop, property=prop,
            changes={'party': party, 'version': prop.submission_version,
                     'from': from_state, 'to': to_state, 'comment': comment[:500]},
        )
    except Exception:  # auditing must never break the workflow
        logger.exception('Failed to write platform audit log for property approval')
    return event


def _notify(user, title, message, prop, **extra):
    if user is None:
        return
    try:
        from apps.notifications.services import notify_user
        notify_user(
            user, title, message, notification_type='general',
            metadata={'property_id': str(prop.id), 'deeplink': f'/properties/{prop.id}'},
            send_sms_too=extra.get('sms', False), send_push=extra.get('send_push', True),
        )
    except Exception:
        logger.exception('Failed to send approval notification')


def _admins():
    from django.contrib.auth import get_user_model
    return get_user_model().objects.filter(role='admin', is_active=True)


def _derive_state(prop, decided):
    """Pure function: review_state implied by a {party: event-like} mapping of decisions."""
    required = required_parties(prop)
    if any(ev.decision == D.REJECTED for ev in decided.values()):
        return S.REJECTED
    if any(ev.decision == D.CHANGES_REQUESTED for ev in decided.values()):
        return S.CHANGES_REQUESTED
    if all(p in decided and decided[p].decision == D.APPROVED for p in required):
        return S.APPROVED
    if P.LANDLORD in required and P.LANDLORD not in decided:
        return S.AWAITING_LANDLORD   # admin may already have approved; listing still waits on the landlord
    return S.AWAITING_ADMIN


def _apply_state(prop, new_state):
    """Persist review_state and keep listing status consistent. Caller holds the row lock."""
    prop.review_state = new_state
    if new_state == S.APPROVED:
        if prop.status == Property.Status.PENDING_APPROVAL:
            prop.status = Property.Status.ACTIVE
    elif prop.status == Property.Status.ACTIVE:
        prop.status = Property.Status.PENDING_APPROVAL
    prop.save(update_fields=['review_state', 'status', 'updated_at'])


# --------------------------------------------------------------------------- public API
@transaction.atomic
def submit(prop, actor):
    """
    Called when a property is created through the API. Decides which approvals are
    required and notifies the reviewers. Admin-created properties are published at once.
    """
    prop = Property.objects.select_for_update().get(pk=prop.pk)
    prop.submitted_by = actor
    if _is_admin(actor):
        prop.requires_landlord_approval = False
    else:
        prop.requires_landlord_approval = actor.id != prop.landlord_id
        if prop.requires_landlord_approval:
            from apps.agencies.permissions import agency_membership_for
            membership = agency_membership_for(actor)
            prop.submitted_by_agency = membership.agency if membership else None
    prop.review_state = S.AWAITING_LANDLORD if prop.requires_landlord_approval else S.AWAITING_ADMIN
    prop.status = Property.Status.PENDING_APPROVAL
    prop.save()

    _log(prop, P.AGENCY if prop.requires_landlord_approval else P.LANDLORD, D.SUBMITTED, actor,
         from_state='', to_state=prop.review_state,
         requires_landlord_approval=prop.requires_landlord_approval)

    if _is_admin(actor):
        # An administrator onboarding a property is itself the admin approval.
        record_decision(prop, actor, D.APPROVED, 'Created by administrator')
        prop.refresh_from_db()
        return prop

    if prop.requires_landlord_approval:
        _notify(prop.landlord, 'Property awaiting your approval',
                f'"{prop.name}" was submitted on your behalf and needs your review before it can be listed.',
                prop, sms=True)
    for admin in _admins():
        _notify(admin, 'Property submitted for review', f'"{prop.name}" is waiting for admin review.', prop,
                send_push=False)
    return prop


@transaction.atomic
def record_decision(prop, actor, decision, comment=''):
    """
    Record an approve / reject / request-changes decision. The party is derived from
    who the actor is - never taken from client input.
    """
    if decision not in (D.APPROVED, D.REJECTED, D.CHANGES_REQUESTED):
        raise ValidationError('Invalid decision.')
    prop = Property.objects.select_for_update().get(pk=prop.pk)

    if _is_admin(actor):
        party = P.ADMIN
    elif actor.id == prop.landlord_id and prop.requires_landlord_approval:
        party = P.LANDLORD
    else:
        raise PermissionDenied('You are not allowed to review this property.')

    if prop.review_state in (S.WITHDRAWN, S.REJECTED):
        raise ValidationError(f'This submission is {prop.get_review_state_display().lower()}; it must be resubmitted.')
    if prop.review_state == S.CHANGES_REQUESTED and decision == D.APPROVED:
        raise ValidationError('Changes were requested; the submitter must resubmit before it can be approved.')
    if decision in (D.REJECTED, D.CHANGES_REQUESTED) and not (comment or '').strip():
        raise ValidationError('A comment is required when rejecting or requesting changes.')

    from types import SimpleNamespace
    old_state = prop.review_state
    decided = current_decisions(prop)
    decided[party] = SimpleNamespace(decision=decision)
    new_state = _derive_state(prop, decided)

    PropertyApproval.objects.create(
        property=prop, party=party, decision=decision, submission_version=prop.submission_version,
        actor=actor, comment=comment or '', from_state=old_state, to_state=new_state,
    )
    _apply_state(prop, new_state)
    try:
        from apps.audit.services import log_action
        log_action(actor=actor, action=f'property.approval.{decision}', target=prop, property=prop,
                   changes={'party': party, 'version': prop.submission_version,
                            'from': old_state, 'to': new_state, 'comment': (comment or '')[:500]})
    except Exception:
        logger.exception('Failed to write platform audit log for property approval')

    # Notifications
    if new_state == S.APPROVED:
        _notify(prop.landlord, 'Property approved and live', f'"{prop.name}" is now published.', prop)
        if prop.submitted_by_id and prop.submitted_by_id != prop.landlord_id:
            _notify(prop.submitted_by, 'Property approved and live', f'"{prop.name}" is now published.', prop)
    elif decision != D.APPROVED:
        label = 'rejected' if decision == D.REJECTED else 'needs changes'
        if prop.submitted_by_id:
            _notify(prop.submitted_by, f'Property {label}', f'"{prop.name}" {label}: {comment}', prop)
        if party == P.ADMIN and prop.requires_landlord_approval:
            _notify(prop.landlord, f'Property {label}', f'Admin review: "{prop.name}" {label}.', prop)
    elif party == P.LANDLORD and new_state == S.AWAITING_ADMIN:
        for admin in _admins():
            _notify(admin, 'Landlord approved - admin review needed', f'"{prop.name}" now awaits admin approval.',
                    prop, send_push=False)
    return prop


@transaction.atomic
def resubmit(prop, actor, comment=''):
    """Submitter (or admin) puts a changes-requested / rejected listing back in review."""
    prop = Property.objects.select_for_update().get(pk=prop.pk)
    if prop.review_state not in (S.CHANGES_REQUESTED, S.REJECTED):
        raise ValidationError('Only a submission with requested changes or a rejection can be resubmitted.')
    old = prop.review_state
    prop.submission_version += 1
    prop.review_state = S.AWAITING_LANDLORD if prop.requires_landlord_approval else S.AWAITING_ADMIN
    prop.status = Property.Status.PENDING_APPROVAL
    prop.save(update_fields=['submission_version', 'review_state', 'status', 'updated_at'])
    _log(prop, P.AGENCY, D.RESUBMITTED, actor, comment, old, prop.review_state)
    if prop.requires_landlord_approval:
        _notify(prop.landlord, 'Property resubmitted', f'"{prop.name}" was updated and needs your review.', prop)
    for admin in _admins():
        _notify(admin, 'Property resubmitted', f'"{prop.name}" was resubmitted for review.', prop, send_push=False)
    return prop


@transaction.atomic
def withdraw(prop, actor, comment=''):
    prop = Property.objects.select_for_update().get(pk=prop.pk)
    if prop.review_state == S.APPROVED:
        raise ValidationError('A published property cannot be withdrawn; suspend or archive it instead.')
    old = prop.review_state
    prop.review_state = S.WITHDRAWN
    prop.status = Property.Status.PENDING_APPROVAL
    prop.save(update_fields=['review_state', 'status', 'updated_at'])
    _log(prop, P.AGENCY, D.WITHDRAWN, actor, comment, old, S.WITHDRAWN)
    return prop


@transaction.atomic
def register_edit(prop, actor, changed_fields):
    """
    Called after an edit. If any material field changed, every earlier approval becomes
    stale: the version is bumped, the listing is unpublished and returned to review.
    Returns True when approvals were invalidated.
    """
    material = sorted(set(changed_fields) & set(material_fields()))
    if not material:
        return False
    prop = Property.objects.select_for_update().get(pk=prop.pk)
    if prop.review_state in (S.WITHDRAWN,):
        return False
    old = prop.review_state
    was_live = prop.status == Property.Status.ACTIVE
    prop.submission_version += 1
    prop.review_state = S.AWAITING_LANDLORD if prop.requires_landlord_approval else S.AWAITING_ADMIN
    if was_live:
        prop.status = Property.Status.PENDING_APPROVAL
    prop.save(update_fields=['submission_version', 'review_state', 'status', 'updated_at'])
    _log(prop, P.SYSTEM, D.INVALIDATED, actor, f"Material edit: {', '.join(material)}", old, prop.review_state,
         changed_fields=material)
    if _is_admin(actor):
        # The administrator made the change, so their sign-off carries to the new version;
        # the landlord (if required) must still approve the changed content.
        record_decision(prop, actor, D.APPROVED, 'Edited by administrator')
        prop.refresh_from_db()
    else:
        if prop.requires_landlord_approval:
            _notify(prop.landlord, 'Property changes need approval',
                    f'"{prop.name}" was edited ({", ".join(material)}) and must be re-approved.', prop)
        for admin in _admins():
            _notify(admin, 'Property edited - re-approval needed', f'"{prop.name}" was edited and is back in review.',
                    prop, send_push=False)
    return True


@transaction.atomic
def set_listing_status(prop, actor, action):
    """Admin suspend / archive / reinstate. Reinstating is only allowed for fully approved listings."""
    prop = Property.objects.select_for_update().get(pk=prop.pk)
    if action == 'suspend':
        prop.status = Property.Status.SUSPENDED
    elif action == 'archive':
        prop.status = Property.Status.ARCHIVED
    elif action == 'reinstate':
        if prop.review_state != S.APPROVED or missing_approvals(prop):
            raise ValidationError('Only a fully approved property can be reinstated.')
        prop.status = Property.Status.ACTIVE
    else:
        raise ValidationError('Invalid action.')
    old = prop.review_state
    prop.save(update_fields=['status', 'updated_at'])
    try:
        from apps.audit.services import log_action
        log_action(actor=actor, action=f'property.{action}', target=prop, property=prop,
                   changes={'review_state': old}, severity='warning')
    except Exception:
        logger.exception('Failed to write platform audit log')
    return prop


def can_view_property(user, prop):
    """
    Server-side visibility rule used by every tenant/public-facing endpoint.
    Unapproved (non-ACTIVE) properties are visible only to people with a real
    relationship to them: admin, owner, submitter, managing agency, or a tenant with a lease.
    """
    if prop.status == Property.Status.ACTIVE:
        return True
    if not (user and user.is_authenticated):
        return False
    if prop.submitted_by_id == user.id:
        return True
    from apps.agencies.permissions import user_can_access_property
    return user_can_access_property(user, prop)


def is_agent_submitter(user, prop):
    """The agency user who submitted this property on the owner's behalf may keep editing
    their own submission (needed for the changes-requested -> edit -> resubmit loop) even
    before a management assignment exists. Material edits still trigger re-approval."""
    return bool(user and user.is_authenticated and prop.requires_landlord_approval
                and prop.submitted_by_id == user.id)
