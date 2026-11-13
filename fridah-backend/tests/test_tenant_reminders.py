from datetime import datetime, timedelta, time
from decimal import Decimal

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.notifications import services as notif_services
from apps.notifications.models import (
    Notification, NotificationDelivery, NotificationPreference, RentReminderLog,
)
from apps.notifications.tasks import retry_failed_deliveries
from apps.payments.tasks import send_payment_reminders
from apps.rentals.models import Invoice


def local(hour, minute=0):
    d = timezone.localdate()
    return timezone.make_aware(datetime(d.year, d.month, d.day, hour, minute))


@pytest.fixture
def sms_calls(monkeypatch):
    calls = []
    monkeypatch.setattr('apps.users.services.send_sms', lambda phone, text: calls.append((phone, text)))
    return calls


@pytest.fixture
def due_soon(lease, tenant):
    return Invoice.objects.create(
        lease=lease, tenant=tenant, invoice_type='rent', amount=Decimal('20000'),
        period_start=timezone.localdate(), period_end=timezone.localdate(),
        due_date=timezone.localdate() + timedelta(days=3),
    )


@pytest.fixture(autouse=True)
def daytime(monkeypatch):
    """Default: not in quiet hours, so reminder tests are independent of when they run."""
    monkeypatch.setattr('apps.notifications.services.in_quiet_hours', lambda user, now=None: False)


@pytest.mark.django_db
class TestQuietHours:
    def test_platform_default_window_crosses_midnight(self, tenant, monkeypatch):
        monkeypatch.undo()  # use the real function
        assert notif_services.in_quiet_hours(tenant, local(23, 0)) is True
        assert notif_services.in_quiet_hours(tenant, local(3, 0)) is True
        assert notif_services.in_quiet_hours(tenant, local(12, 0)) is False
        assert notif_services.in_quiet_hours(tenant, local(7, 0)) is False   # window ends at 07:00

    def test_user_window_overrides_default_and_can_be_disabled_platform_wide(self, tenant, monkeypatch):
        monkeypatch.undo()
        NotificationPreference.objects.create(user=tenant, quiet_hours_start=time(13, 0), quiet_hours_end=time(14, 0))
        assert notif_services.in_quiet_hours(tenant, local(13, 30)) is True
        assert notif_services.in_quiet_hours(tenant, local(23, 0)) is False
        NotificationPreference.objects.filter(user=tenant).update(quiet_hours_start=None, quiet_hours_end=None)
        with override_settings(NOTIFICATION_DEFAULT_QUIET_HOURS=None):
            assert notif_services.in_quiet_hours(tenant, local(23, 0)) is False


@pytest.mark.django_db
class TestReminderEngine:
    def test_sends_once_with_deeplink_and_balance(self, due_soon, tenant, sms_calls):
        due_soon.amount_paid = Decimal('5000')
        due_soon.status = Invoice.Status.PARTIALLY_PAID
        due_soon.save()
        assert send_payment_reminders()['sent'] == 1
        n = Notification.objects.get(user=tenant, metadata__trigger='due_in_3')
        assert 'KES 15,000.00' in n.message                     # outstanding balance, not the full amount
        assert n.metadata['deeplink'] == f'/tenant/invoices?invoice={due_soon.id}'
        assert len(sms_calls) == 1
        assert send_payment_reminders()['sent'] == 0           # hourly re-run: no duplicate
        assert Notification.objects.filter(user=tenant, metadata__trigger='due_in_3').count() == 1
        assert RentReminderLog.objects.filter(invoice=due_soon).count() == 1

    def test_message_names_the_charge_type_and_has_no_credentials(self, due_soon, tenant, sms_calls):
        due_soon.invoice_type = 'amenity'
        due_soon.save()
        send_payment_reminders()
        msg = Notification.objects.get(user=tenant).message
        assert 'amenity charge' in msg
        assert not any(w in msg.lower() for w in ('pin', 'password', 'token'))

    def test_quiet_hours_hold_back_then_send_later(self, due_soon, tenant, sms_calls, monkeypatch):
        monkeypatch.setattr('apps.notifications.services.in_quiet_hours', lambda user, now=None: True)
        stats = send_payment_reminders()
        assert stats['held_quiet_hours'] == 1 and stats['sent'] == 0
        assert not Notification.objects.filter(user=tenant).exists() and not RentReminderLog.objects.exists()
        monkeypatch.setattr('apps.notifications.services.in_quiet_hours', lambda user, now=None: False)
        assert send_payment_reminders()['sent'] == 1                # next run after the window

    def test_payment_alerts_off_keeps_in_app_but_skips_sms(self, due_soon, tenant, sms_calls):
        NotificationPreference.objects.create(user=tenant, payment_alerts=False)
        send_payment_reminders()
        n = Notification.objects.get(user=tenant)
        assert sms_calls == []
        sms = n.deliveries.get(channel='sms')
        assert sms.status == NotificationDelivery.Status.SKIPPED and 'disabled' in sms.error_message

    def test_overdue_reminder_fires_once(self, due_soon, tenant, sms_calls):
        due_soon.due_date = timezone.localdate() - timedelta(days=2)
        due_soon.status = Invoice.Status.OVERDUE
        due_soon.save()
        send_payment_reminders()
        send_payment_reminders()
        assert Notification.objects.filter(user=tenant, title='Payment overdue').count() == 1

    def test_one_failure_does_not_stop_the_rest(self, due_soon, lease, tenant, sms_calls, monkeypatch):
        second = Invoice.objects.create(
            lease=lease, tenant=tenant, invoice_type='rent', amount=100, period_start=due_soon.period_start,
            period_end=due_soon.period_end, due_date=due_soon.due_date)
        real = notif_services.notify_user
        seen = []

        def flaky(user, *a, **kw):
            seen.append(1)
            if len(seen) == 1:
                raise RuntimeError('boom')
            return real(user, *a, **kw)

        monkeypatch.setattr('apps.notifications.services.notify_user', flaky)
        stats = send_payment_reminders()
        assert stats['failed'] == 1 and stats['sent'] == 1


@pytest.mark.django_db
class TestDeliveryRetry:
    def _failed(self, tenant):
        n = Notification.objects.create(user=tenant, title='T', message='M')
        return NotificationDelivery.objects.create(notification=n, channel='sms', status='failed', error_message='gateway')

    def test_failed_sms_is_retried_and_recorded(self, tenant, monkeypatch):
        d = self._failed(tenant)
        monkeypatch.setattr('apps.users.services.send_sms', lambda phone, text: None)
        assert retry_failed_deliveries() == {'retried': 1, 'recovered': 1}
        d.refresh_from_db()
        assert d.status == 'sent' and d.attempts == 2 and d.sent_at

    def test_gives_up_after_max_attempts(self, tenant, monkeypatch):
        d = self._failed(tenant)

        def boom(phone, text):
            raise RuntimeError('still down')

        monkeypatch.setattr('apps.users.services.send_sms', boom)
        for _ in range(5):
            retry_failed_deliveries()
        d.refresh_from_db()
        assert d.status == 'failed' and d.attempts == 3 and 'still down' in d.error_message


@pytest.mark.django_db
def test_quiet_hours_round_trip_through_preferences_api(api_client, tenant):
    api_client.force_authenticate(user=tenant)
    r = api_client.patch('/api/v1/notification-preferences/',
                         {'quiet_hours_start': '22:00', 'quiet_hours_end': '06:30', 'payment_alerts': False}, format='json')
    assert r.status_code == 200
    got = api_client.get('/api/v1/notification-preferences/')
    body = got.data.get('data', got.data)
    assert body['quiet_hours_start'].startswith('22:00') and body['quiet_hours_end'].startswith('06:30')
    assert body['payment_alerts'] is False
    r = api_client.patch('/api/v1/notification-preferences/', {'quiet_hours_start': None, 'quiet_hours_end': None}, format='json')
    assert r.status_code == 200
