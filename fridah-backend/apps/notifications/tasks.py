import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
RETRY_WINDOW_HOURS = 24


@shared_task
def retry_failed_deliveries():
    """Retry failed SMS/push deliveries a bounded number of times; every attempt is recorded."""
    from .models import NotificationDelivery as D
    from .services import _send_push
    since = timezone.now() - timedelta(hours=RETRY_WINDOW_HOURS)
    failed = D.objects.filter(
        status=D.Status.FAILED, attempts__lt=MAX_ATTEMPTS, created_at__gte=since,
        channel__in=[D.Channel.SMS, D.Channel.PUSH],
    ).select_related('notification__user')
    retried = recovered = 0
    for delivery in failed:
        notif, user = delivery.notification, delivery.notification.user
        retried += 1
        try:
            if delivery.channel == D.Channel.SMS:
                from apps.users.services import send_sms
                send_sms(user.phone_number, f'{notif.title}: {notif.message}')
                ok = True
            else:
                ok = bool(user.fcm_token) and _send_push(user.fcm_token, notif.title, notif.message)
            delivery.error_message = '' if ok else 'push not delivered'
        except Exception as exc:
            ok = False
            delivery.error_message = str(exc)[:255]
        delivery.attempts += 1
        if ok:
            delivery.status, delivery.sent_at = D.Status.SENT, timezone.now()
            recovered += 1
        delivery.save(update_fields=['attempts', 'status', 'sent_at', 'error_message'])
    return {'retried': retried, 'recovered': recovered}
