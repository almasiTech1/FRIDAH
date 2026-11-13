"""Rate limits and the M-Pesa callback check must agree about who the real client is, and a fake header can't change it."""
from django.conf import settings
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from rest_framework.throttling import BaseThrottle

from apps.payments.security import get_client_ip

factory = APIRequestFactory()


def request(forwarded, remote='10.0.0.9'):
    r = factory.get('/', HTTP_X_FORWARDED_FOR=forwarded, REMOTE_ADDR=remote)
    return Request(r)


def test_one_setting_drives_both():
    from rest_framework.settings import api_settings
    assert settings.REST_FRAMEWORK['NUM_PROXIES'] == settings.TRUSTED_PROXY_COUNT
    assert api_settings.NUM_PROXIES == settings.TRUSTED_PROXY_COUNT


def test_a_forged_forwarded_header_does_not_change_the_identity_used_for_rate_limits():
    throttle = BaseThrottle()
    # nginx appends the real address to whatever the caller sent, so the real client is always the last entry
    a = throttle.get_ident(request('6.6.6.6, 203.0.113.7'))
    b = throttle.get_ident(request('9.9.9.9, 203.0.113.7'))
    c = throttle.get_ident(request('203.0.113.7'))
    assert a == b == c == '203.0.113.7'


def test_rate_limit_and_mpesa_check_see_the_same_client():
    req = request('6.6.6.6, 203.0.113.7')
    assert BaseThrottle().get_ident(req) == get_client_ip(req._request) == '203.0.113.7'
