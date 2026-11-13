import logging
from django.db import transaction
from django.utils import timezone

from .messaging_models import (
    MessageThread, MessageParticipant, Message, MessageAttachment, MessageDeliveryStatus,
    SharedObject, MessageReaction, CallLog,
)

logger = logging.getLogger('apps.notifications.chat')


class RelationshipError(Exception):
    """Raised when two users have no legitimate relationship justifying a new chat thread."""


def _active_lease_between(tenant, landlord_or_property_owner=None):
    from apps.rentals.models import Lease
    qs = Lease.objects.filter(tenant=tenant, status=Lease.Status.ACTIVE)
    if landlord_or_property_owner is not None:
        qs = qs.filter(unit__property__landlord=landlord_or_property_owner)
    return qs.select_related('unit__property')


def users_share_relationship(user_a, user_b):
    """
    True if user_a and user_b have a legitimate relationship justifying a chat thread:
    ownership, an active lease, an active agency management assignment covering a
    shared property, an assigned maintenance/service job, or agency colleagueship.
    Platform admins can always start a thread.
    """
    if user_a.id == user_b.id:
        return False
    if user_a.role == 'admin' or user_b.role == 'admin' or user_a.is_staff or user_b.is_staff:
        return True

    from apps.agencies.permissions import agency_membership_for
    from apps.agencies.models import PropertyManagementAssignment, PropertyStaffAssignment
    from apps.rentals.models import Lease
    from apps.services.models import ServiceJob

    # Same agency, both active staff -> colleagues.
    membership_a = agency_membership_for(user_a)
    membership_b = agency_membership_for(user_b)
    if membership_a and membership_b and membership_a.agency_id == membership_b.agency_id:
        return True

    # Landlord <-> tenant via an active lease on the landlord's property.
    if _active_lease_between(user_a, user_b).exists() or _active_lease_between(user_b, user_a).exists():
        return True

    # Tenant <-> agency staff / caretaker, or Landlord <-> agency staff, via an active
    # management assignment on a property either of them is connected to.
    for tenant_side, staff_side in ((user_a, user_b), (user_b, user_a)):
        membership = agency_membership_for(staff_side)
        if not membership:
            continue
        assigned_property_ids = PropertyManagementAssignment.objects.filter(
            agency=membership.agency, status=PropertyManagementAssignment.Status.ACTIVE
        ).values_list('property_id', flat=True)
        if Lease.objects.filter(
            tenant=tenant_side, status=Lease.Status.ACTIVE, unit__property_id__in=assigned_property_ids
        ).exists():
            return True
        from apps.properties.models import Property
        if Property.objects.filter(id__in=assigned_property_ids, landlord=tenant_side).exists():
            return True

    # Service-job assignment: either side is the assigned provider and the other the
    # job's poster (landlord/agency staff).
    from django.db.models import Q
    job_match = ServiceJob.objects.filter(
        Q(assigned_provider=user_a, posted_by=user_b) | Q(assigned_provider=user_b, posted_by=user_a)
    ).exists()
    if job_match:
        return True

    # Hotel/BnB host <-> guest via any booking between them (current or past —
    # a guest should still be able to follow up on a stay after checkout).
    from apps.bookings.models import Booking
    booking_match = Booking.objects.filter(
        Q(host=user_a, guest=user_b) | Q(host=user_b, guest=user_a)
    ).exists()
    if booking_match:
        return True

    return False


def get_or_create_direct_thread(*, user, other_user, thread_type=None, lease=None, property=None, service_job=None):
    if not users_share_relationship(user, other_user):
        raise RelationshipError(
            "You can only message people you have an active relationship with on FRIDAH "
            "(as your landlord, tenant, agency, caretaker, or an assigned service provider)."
        )

    existing = MessageThread.objects.filter(
        is_group=False, participants=user
    ).filter(participants=other_user).first()
    if existing:
        return existing, False

    resolved_type = thread_type or _infer_thread_type(user, other_user)
    thread = MessageThread.objects.create(
        thread_type=resolved_type, lease=lease, property=property, service_job=service_job,
        created_by=user, is_group=False,
    )
    MessageParticipant.objects.create(thread=thread, user=user, is_admin=True, joined_at=timezone.now())
    MessageParticipant.objects.create(thread=thread, user=other_user, joined_at=timezone.now())
    return thread, True


def _infer_thread_type(user, other_user):
    from apps.agencies.permissions import agency_membership_for
    from apps.bookings.models import Booking
    from django.db.models import Q

    if Booking.objects.filter(
        Q(host=user, guest=other_user) | Q(host=other_user, guest=user)
    ).exists():
        return MessageThread.ThreadType.HOTEL_GUEST
    if user.role == 'tenant' or other_user.role == 'tenant':
        staff_side = other_user if user.role == 'tenant' else user
        if agency_membership_for(staff_side):
            role_type = agency_membership_for(staff_side).role.role_type
            if role_type == 'caretaker':
                return MessageThread.ThreadType.TENANT_CARETAKER
            return MessageThread.ThreadType.TENANT_AGENCY
        if staff_side.role == 'landlord':
            return MessageThread.ThreadType.TENANT_LANDLORD
        return MessageThread.ThreadType.TENANT_PROVIDER
    if user.role == 'landlord' or other_user.role == 'landlord':
        return MessageThread.ThreadType.LANDLORD_AGENCY
    return MessageThread.ThreadType.DIRECT


@transaction.atomic
def create_group_thread(*, created_by, property, participants, subject=''):
    """Create a property-group chat (owner/agency staff + optionally tenants)."""
    thread = MessageThread.objects.create(
        thread_type=MessageThread.ThreadType.PROPERTY_GROUP, property=property,
        created_by=created_by, is_group=True, subject=subject or f"{property.name} Group",
    )
    all_participants = set(participants) | {created_by}
    for i, participant in enumerate(all_participants):
        MessageParticipant.objects.create(
            thread=thread, user=participant, is_admin=(participant == created_by), joined_at=timezone.now()
        )
    return thread


@transaction.atomic
def send_message(
    *, thread, sender, body='', message_type=Message.MessageType.TEXT, shared_object=None, reply_to=None,
    attachments=None,
):
    if not MessageParticipant.objects.filter(thread=thread, user=sender, left_at__isnull=True).exists():
        raise RelationshipError("You are not a participant of this conversation.")

    message = Message.objects.create(
        thread=thread, sender=sender, body=body, message_type=message_type,
        shared_object=shared_object, reply_to=reply_to,
    )
    for attachment_data in (attachments or []):
        MessageAttachment.objects.create(message=message, **attachment_data)

    recipients = MessageParticipant.objects.filter(thread=thread, left_at__isnull=True).exclude(user=sender)
    for participant in recipients:
        MessageDeliveryStatus.objects.create(
            message=message, user=participant.user,
            status=MessageDeliveryStatus.Status.DELIVERED, delivered_at=timezone.now(),
        )

    thread.save(update_fields=[])  # bump updated_at via auto_now

    for participant in recipients:
        try:
            from .services import notify_user
            preview = body[:100] if body else f"Sent a {message.get_message_type_display().lower()}"
            notify_user(
                participant.user, title=f"New message from {sender.get_full_name()}",
                message=preview, notification_type='general',
                metadata={'thread_id': str(thread.id), 'message_id': str(message.id)},
            )
        except Exception:
            logger.exception("Failed to notify chat recipient")

    return message


def share_object(*, user, thread, obj, object_type, card_data=None, reply_to=None):
    """Attach a live object (invoice, payment, property, maintenance request, etc.) as a rich chat card."""
    from django.contrib.contenttypes.models import ContentType
    shared = SharedObject.objects.create(
        object_type=object_type, content_type=ContentType.objects.get_for_model(obj),
        object_id=obj.id, card_data=card_data or {}, shared_by=user,
    )
    message_type_map = {
        SharedObject.ObjectType.PROPERTY: Message.MessageType.PROPERTY_CARD,
        SharedObject.ObjectType.UNIT: Message.MessageType.PROPERTY_CARD,
        SharedObject.ObjectType.INVOICE: Message.MessageType.INVOICE_CARD,
        SharedObject.ObjectType.PAYMENT: Message.MessageType.PAYMENT_REQUEST,
        SharedObject.ObjectType.MAINTENANCE_REQUEST: Message.MessageType.MAINTENANCE_CARD,
        SharedObject.ObjectType.SERVICE_JOB: Message.MessageType.MAINTENANCE_CARD,
        SharedObject.ObjectType.BOOKING: Message.MessageType.BOOKING_CARD,
        SharedObject.ObjectType.LEASE: Message.MessageType.LEASE_CARD,
        SharedObject.ObjectType.DOCUMENT: Message.MessageType.LEASE_CARD,
    }
    return send_message(
        thread=thread, sender=user, message_type=message_type_map.get(object_type, Message.MessageType.TEXT),
        shared_object=shared, reply_to=reply_to,
    )


def react_to_message(*, message, user, emoji):
    reaction, _ = MessageReaction.objects.get_or_create(message=message, user=user, emoji=emoji)
    return reaction


def remove_reaction(*, message, user, emoji):
    MessageReaction.objects.filter(message=message, user=user, emoji=emoji).delete()


def log_call(*, thread, caller, callee, call_type=CallLog.CallType.VOICE):
    if not users_share_relationship(caller, callee):
        raise RelationshipError("You can only call people you have an active relationship with on FRIDAH.")
    return CallLog.objects.create(thread=thread, caller=caller, callee=callee, call_type=call_type)


def update_call_status(call, status, *, answered=False):
    call.status = status
    if answered and not call.answered_at:
        call.answered_at = timezone.now()
    if status in (CallLog.Status.COMPLETED, CallLog.Status.MISSED, CallLog.Status.REJECTED, CallLog.Status.FAILED):
        call.ended_at = timezone.now()
        if call.answered_at:
            call.duration_seconds = int((call.ended_at - call.answered_at).total_seconds())
    call.save()
    return call
