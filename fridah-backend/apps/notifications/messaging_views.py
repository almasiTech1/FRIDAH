from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound
from django.shortcuts import get_object_or_404

from apps.users.permissions import IsLandlordOrAdmin
from .messaging_models import (
    MessageThread, MessageParticipant, Message, MessageAttachment, MessageReaction,
    MessageDeliveryStatus, SharedObject, CallLog, Announcement,
)
from . import messaging_services as services


def success(data=None, message="OK", status_code=status.HTTP_200_OK):
    return Response({'success': True, 'message': message, 'data': data}, status=status_code)


def error(message, status_code=status.HTTP_400_BAD_REQUEST):
    return Response({'success': False, 'error': {'message': message}}, status=status_code)


def _serialize_message(m, viewer):
    reactions = {}
    for r in m.reactions.all():
        reactions.setdefault(r.emoji, []).append(str(r.user_id))
    delivery = m.delivery_statuses.filter(user=viewer).first()
    return {
        'id': str(m.id),
        'thread_id': str(m.thread_id),
        'sender_id': str(m.sender_id) if m.sender_id else None,
        'sender_name': m.sender.get_full_name() if m.sender else 'FRIDAH',
        'message_type': m.message_type,
        'body': m.body,
        'attachment_url': m.attachment.url if m.attachment else None,
        'attachments': [
            {
                'id': str(a.id), 'url': a.file.url, 'file_type': a.file_type,
                'duration_seconds': a.duration_seconds, 'thumbnail_url': a.thumbnail.url if a.thumbnail else None,
            } for a in m.attachments.all()
        ],
        'shared_object': {
            'id': str(m.shared_object.id), 'object_type': m.shared_object.object_type,
            'card_data': m.shared_object.card_data,
        } if m.shared_object else None,
        'reply_to_id': str(m.reply_to_id) if m.reply_to_id else None,
        'reactions': reactions,
        'is_edited': m.is_edited,
        'is_deleted': m.is_deleted,
        'delivery_status': delivery.status if delivery else ('sent' if m.sender_id == viewer.id else None),
        'created_at': str(m.created_at),
    }


class MessageThreadListView(APIView):
    def get(self, request):
        threads = MessageThread.objects.filter(
            participants=request.user, thread_participants__left_at__isnull=True
        ).order_by('-updated_at')
        data = []
        for t in threads:
            last = t.messages.order_by('-created_at').first()
            others = t.participants.exclude(id=request.user.id)
            data.append({
                'id': str(t.id),
                'thread_type': t.thread_type,
                'subject': t.subject,
                'is_group': t.is_group,
                'property_id': str(t.property_id) if t.property_id else None,
                'unread_count': t.unread_count_for(request.user),
                'participants': [{'id': str(u.id), 'name': u.get_full_name(), 'role': u.role} for u in others],
                'last_message': {
                    'body': last.body, 'message_type': last.message_type,
                    'created_at': str(last.created_at),
                    'sender': last.sender.get_full_name() if last.sender else 'FRIDAH',
                } if last else None,
                'updated_at': str(t.updated_at),
            })
        return success(data)

    def post(self, request):
        """Start a new direct thread with someone you have a legitimate relationship with."""
        participant_id = request.data.get('participant_id')
        body = request.data.get('body', '')
        lease_id = request.data.get('lease_id')

        from apps.users.models import User
        try:
            other = User.objects.get(id=participant_id)
        except User.DoesNotExist:
            return error("User not found.", status.HTTP_404_NOT_FOUND)

        lease = None
        if lease_id:
            from apps.rentals.models import Lease
            lease = get_object_or_404(Lease, id=lease_id)

        try:
            thread, created = services.get_or_create_direct_thread(user=request.user, other_user=other, lease=lease)
        except services.RelationshipError as e:
            return error(str(e), status.HTTP_403_FORBIDDEN)

        if body:
            services.send_message(thread=thread, sender=request.user, body=body)

        return success(
            {'thread_id': str(thread.id), 'created': created},
            message="Thread ready." if created else "Existing thread.",
            status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class PropertyGroupThreadView(APIView):
    """Create a property-wide group chat (owner/agency staff, optionally + tenants)."""
    permission_classes = [IsLandlordOrAdmin]

    def post(self, request):
        from apps.properties.models import Property
        from apps.users.models import User
        from apps.agencies.permissions import user_can_access_property

        property = get_object_or_404(Property, id=request.data.get('property_id'))
        if not user_can_access_property(request.user, property):
            raise PermissionDenied("You do not manage this property.")

        participant_ids = request.data.get('participant_ids', [])
        participants = list(User.objects.filter(id__in=participant_ids))
        thread = services.create_group_thread(
            created_by=request.user, property=property, participants=participants,
            subject=request.data.get('subject', ''),
        )
        return success({'thread_id': str(thread.id)}, message="Group created.", status_code=status.HTTP_201_CREATED)


class MessageListView(APIView):
    def get(self, request, thread_id):
        thread = get_object_or_404(MessageThread, id=thread_id, participants=request.user)
        thread.mark_read_for(request.user)
        Message.objects.filter(thread=thread, is_read=False).exclude(sender=request.user).update(is_read=True)
        msgs = thread.messages.filter(is_deleted=False).select_related('sender', 'shared_object').prefetch_related(
            'reactions', 'attachments', 'delivery_statuses'
        )
        data = [_serialize_message(m, request.user) for m in msgs]
        return success(data)

    def post(self, request, thread_id):
        thread = get_object_or_404(MessageThread, id=thread_id, participants=request.user)
        body = request.data.get('body', '').strip()
        message_type = request.data.get('message_type', Message.MessageType.TEXT)
        reply_to = None
        if request.data.get('reply_to_id'):
            reply_to = get_object_or_404(Message, id=request.data['reply_to_id'], thread=thread)

        if not body and message_type == Message.MessageType.TEXT:
            return error("Message body cannot be empty.")

        try:
            msg = services.send_message(
                thread=thread, sender=request.user, body=body, message_type=message_type, reply_to=reply_to,
            )
        except services.RelationshipError as e:
            return error(str(e), status.HTTP_403_FORBIDDEN)

        return success(_serialize_message(msg, request.user), status_code=status.HTTP_201_CREATED)


class MessageAttachmentUploadView(APIView):
    """Upload one or more files (image/video/document/voice note) attached to a new message."""
    def post(self, request, thread_id):
        thread = get_object_or_404(MessageThread, id=thread_id, participants=request.user)
        files = request.FILES.getlist('files')
        if not files:
            return error("No files provided.")

        file_type = request.data.get('file_type', MessageAttachment.FileType.DOCUMENT)
        message_type = {
            MessageAttachment.FileType.IMAGE: Message.MessageType.IMAGE,
            MessageAttachment.FileType.VIDEO: Message.MessageType.VIDEO,
            MessageAttachment.FileType.VOICE_NOTE: Message.MessageType.VOICE_NOTE,
        }.get(file_type, Message.MessageType.DOCUMENT)

        attachments = [{
            'file': f, 'file_type': file_type,
            'duration_seconds': request.data.get('duration_seconds') or None,
            'file_size_bytes': f.size,
        } for f in files]

        try:
            msg = services.send_message(
                thread=thread, sender=request.user, body=request.data.get('caption', ''),
                message_type=message_type, attachments=attachments,
            )
        except services.RelationshipError as e:
            return error(str(e), status.HTTP_403_FORBIDDEN)

        return success(_serialize_message(msg, request.user), status_code=status.HTTP_201_CREATED)


class ShareObjectView(APIView):
    """Share a live property/invoice/payment/maintenance-request/booking/lease as a rich card in a thread."""
    OBJECT_MODEL_MAP = {
        SharedObject.ObjectType.PROPERTY: ('apps.properties.models', 'Property'),
        SharedObject.ObjectType.UNIT: ('apps.properties.models', 'Unit'),
        SharedObject.ObjectType.INVOICE: ('apps.rentals.models', 'Invoice'),
        SharedObject.ObjectType.PAYMENT: ('apps.payments.models', 'Payment'),
        SharedObject.ObjectType.MAINTENANCE_REQUEST: ('apps.rentals.models', 'MaintenanceRequest'),
        SharedObject.ObjectType.SERVICE_JOB: ('apps.services.models', 'ServiceJob'),
        SharedObject.ObjectType.BOOKING: ('apps.bookings.models', 'Booking'),
        SharedObject.ObjectType.LEASE: ('apps.rentals.models', 'Lease'),
    }

    def post(self, request, thread_id):
        import importlib
        thread = get_object_or_404(MessageThread, id=thread_id, participants=request.user)
        object_type = request.data.get('object_type')
        object_id = request.data.get('object_id')
        card_data = request.data.get('card_data', {})

        mapping = self.OBJECT_MODEL_MAP.get(object_type)
        if not mapping:
            return error("Unsupported object_type.")
        module = importlib.import_module(mapping[0])
        model = getattr(module, mapping[1])
        obj = get_object_or_404(model, id=object_id)

        try:
            msg = services.share_object(
                user=request.user, thread=thread, obj=obj, object_type=object_type, card_data=card_data
            )
        except services.RelationshipError as e:
            return error(str(e), status.HTTP_403_FORBIDDEN)
        return success(_serialize_message(msg, request.user), status_code=status.HTTP_201_CREATED)


class MessageReactionView(APIView):
    def post(self, request, message_id):
        message = get_object_or_404(Message, id=message_id, thread__participants=request.user)
        emoji = request.data.get('emoji', '👍')
        services.react_to_message(message=message, user=request.user, emoji=emoji)
        return success(message="Reaction added.")

    def delete(self, request, message_id):
        message = get_object_or_404(Message, id=message_id, thread__participants=request.user)
        emoji = request.query_params.get('emoji', '👍')
        services.remove_reaction(message=message, user=request.user, emoji=emoji)
        return success(message="Reaction removed.")


class CallLogView(APIView):
    def post(self, request):
        from apps.users.models import User
        thread = None
        if request.data.get('thread_id'):
            thread = get_object_or_404(MessageThread, id=request.data['thread_id'], participants=request.user)
        callee = get_object_or_404(User, id=request.data.get('callee_id'))
        call_type = request.data.get('call_type', CallLog.CallType.VOICE)
        try:
            call = services.log_call(thread=thread, caller=request.user, callee=callee, call_type=call_type)
        except services.RelationshipError as e:
            return error(str(e), status.HTTP_403_FORBIDDEN)
        return success({'id': str(call.id), 'callee_phone': callee.phone_number}, status_code=status.HTTP_201_CREATED)


class CallStatusUpdateView(APIView):
    def post(self, request, id):
        call = get_object_or_404(CallLog, id=id)
        if request.user.id not in (call.caller_id, call.callee_id):
            raise PermissionDenied("Not part of this call.")
        new_status = request.data.get('status')
        if new_status not in CallLog.Status.values:
            return error("Invalid status.")
        services.update_call_status(call, new_status, answered=(new_status == CallLog.Status.ANSWERED))
        return success(message="Call status updated.")


class AnnouncementView(APIView):
    def post(self, request):
        from apps.properties.models import Property
        from apps.rentals.models import Lease
        from apps.users.services import send_sms
        from apps.agencies.permissions import user_can_access_property, managing_agency_for_property

        property_id = request.data.get('property_id')
        title = request.data.get('title', '')
        body = request.data.get('body', '')
        send_sms_flag = request.data.get('send_sms', False)

        prop = get_object_or_404(Property, id=property_id)
        if not user_can_access_property(request.user, prop, required_permission='property.manage'):
            raise PermissionDenied("You cannot post announcements for this property.")

        ann = Announcement.objects.create(
            property=prop, posted_by=request.user, agency=managing_agency_for_property(prop),
            title=title, body=body, send_sms=send_sms_flag,
        )

        active_leases = Lease.objects.filter(unit__property=prop, status='active')
        notified = 0
        for lease in active_leases:
            try:
                from .services import notify_user
                notify_user(lease.tenant, title=f"📢 {title}", message=body, notification_type='general')
                if send_sms_flag:
                    send_sms(lease.tenant.phone_number, f"FRIDAH Notice — {title}: {body}")
                notified += 1
            except Exception:
                pass

        return success(
            {'announcement_id': str(ann.id), 'tenants_notified': notified},
            message=f"Announcement sent to {notified} tenant(s).",
        )


class MyRelationshipsView(APIView):
    """Everyone the caller has a legitimate relationship with — used to populate the 'new chat' picker."""
    def get(self, request):
        from apps.agencies.permissions import agency_membership_for
        from apps.agencies.models import PropertyManagementAssignment, AgencyMembership
        from apps.rentals.models import Lease
        from apps.users.models import User

        user = request.user
        people = {}

        def add(u, relationship):
            if u.id == user.id:
                return
            entry = people.setdefault(
                str(u.id), {'id': str(u.id), 'name': u.get_full_name(), 'role': u.role, 'relationships': []}
            )
            if relationship not in entry['relationships']:
                entry['relationships'].append(relationship)

        for lease in Lease.objects.filter(tenant=user, status=Lease.Status.ACTIVE).select_related('unit__property__landlord'):
            add(lease.unit.property.landlord, 'landlord')
        for lease in Lease.objects.filter(unit__property__landlord=user, status=Lease.Status.ACTIVE).select_related('tenant'):
            add(lease.tenant, 'tenant')

        membership = agency_membership_for(user)
        if membership:
            for colleague in AgencyMembership.objects.filter(
                agency=membership.agency, status=AgencyMembership.Status.ACTIVE
            ).exclude(user=user).select_related('user'):
                add(colleague.user, 'colleague')
            assigned_property_ids = list(PropertyManagementAssignment.objects.filter(
                agency=membership.agency, status=PropertyManagementAssignment.Status.ACTIVE
            ).values_list('property_id', flat=True))
            for lease in Lease.objects.filter(
                unit__property_id__in=assigned_property_ids, status=Lease.Status.ACTIVE
            ).select_related('tenant'):
                add(lease.tenant, 'tenant')
            for owner in User.objects.filter(properties__id__in=assigned_property_ids).distinct():
                add(owner, 'property_owner')

        return success(list(people.values()))
