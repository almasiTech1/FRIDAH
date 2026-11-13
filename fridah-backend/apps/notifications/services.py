import logging
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger('django')


def _parse_hhmm(value):
    from datetime import time
    h, m = value.split(':')
    return time(int(h), int(m))


def in_quiet_hours(user, now=None):
    """True when `now` (local time) falls inside the user's quiet window (or the platform default).
    Windows may cross midnight, e.g. 21:00-07:00."""
    from django.utils import timezone
    from .models import NotificationPreference
    prefs = NotificationPreference.objects.filter(user=user).first()
    start = getattr(prefs, 'quiet_hours_start', None)
    end = getattr(prefs, 'quiet_hours_end', None)
    if not (start and end):
        default = getattr(settings, 'NOTIFICATION_DEFAULT_QUIET_HOURS', None)
        if not default:
            return False
        start, end = _parse_hhmm(default[0]), _parse_hhmm(default[1])
    local = timezone.localtime(now or timezone.now()).time()
    if start == end:
        return False
    if start < end:
        return start <= local < end
    return local >= start or local < end


def notify_user(user, title, message, notification_type='general', metadata=None, send_sms_too=False, send_push=True,
                alert_category=None):
    """Creates an in-app notification and optionally dispatches SMS/push, respecting preferences.
    Every channel attempt is recorded on NotificationDelivery for auditability.

    alert_category='payment' additionally honours the user's payment_alerts preference: the in-app
    notification is always kept (so nothing is hidden), but SMS/push are skipped when the user
    has switched those alerts off."""
    from django.utils import timezone
    from .models import Notification, NotificationPreference, NotificationDelivery

    notif = Notification.objects.create(
        user=user, title=title, message=message,
        notification_type=notification_type, metadata=metadata or {}
    )
    NotificationDelivery.objects.create(
        notification=notif, channel=NotificationDelivery.Channel.IN_APP,
        status=NotificationDelivery.Status.SENT, sent_at=timezone.now(),
    )

    prefs, _ = NotificationPreference.objects.get_or_create(user=user)
    if alert_category == 'payment' and not prefs.payment_alerts:
        for channel, wanted in ((NotificationDelivery.Channel.PUSH, send_push), (NotificationDelivery.Channel.SMS, send_sms_too)):
            if wanted:
                NotificationDelivery.objects.create(
                    notification=notif, channel=channel, status=NotificationDelivery.Status.SKIPPED,
                    error_message='payment alerts disabled by user',
                )
        return notif

    if send_push:
        if prefs.push_enabled and user.fcm_token:
            ok = _send_push(user.fcm_token, title, message)
            NotificationDelivery.objects.create(
                notification=notif, channel=NotificationDelivery.Channel.PUSH,
                status=NotificationDelivery.Status.SENT if ok else NotificationDelivery.Status.FAILED,
                sent_at=timezone.now() if ok else None,
            )
        elif not prefs.push_enabled:
            NotificationDelivery.objects.create(
                notification=notif, channel=NotificationDelivery.Channel.PUSH, status=NotificationDelivery.Status.SKIPPED,
            )

    if send_sms_too:
        if prefs.sms_enabled:
            from apps.users.services import send_sms
            try:
                send_sms(user.phone_number, f"{title}: {message}")
                NotificationDelivery.objects.create(
                    notification=notif, channel=NotificationDelivery.Channel.SMS,
                    status=NotificationDelivery.Status.SENT, sent_at=timezone.now(),
                )
            except Exception as e:
                NotificationDelivery.objects.create(
                    notification=notif, channel=NotificationDelivery.Channel.SMS,
                    status=NotificationDelivery.Status.FAILED, error_message=str(e)[:255],
                    # retried by apps.notifications.tasks.retry_failed_deliveries
                )
        else:
            NotificationDelivery.objects.create(
                notification=notif, channel=NotificationDelivery.Channel.SMS, status=NotificationDelivery.Status.SKIPPED,
            )

    return notif


def _send_push(fcm_token, title, body):
    """Send via Firebase Cloud Messaging. No-op gracefully if not configured. Returns True on success."""
    try:
        import firebase_admin
        from firebase_admin import messaging
        if not firebase_admin._apps:
            logger.info("Firebase not configured; skipping push notification.")
            return False
        msg = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            token=fcm_token,
        )
        messaging.send(msg)
        return True
    except Exception as e:
        logger.warning("Push notification failed: %s", e)
        return False


def send_email_notification(user, subject, message):
    if not user.email:
        return
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
    except Exception as e:
        logger.error("Email send failed: %s", e)
