import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.core.management.utils import get_random_secret_key
from django.test import Client, override_settings

BACKEND = Path(__file__).resolve().parent.parent


@pytest.mark.django_db
class TestAdminAllowlist:
    def get(self, forwarded):
        return Client().get('/admin/login/', HTTP_X_FORWARDED_FOR=forwarded, REMOTE_ADDR='10.0.0.9')

    def test_open_to_everyone_when_no_list_is_configured(self):
        assert self.get('203.0.113.7').status_code == 200

    @override_settings(ADMIN_ALLOWED_IPS=['203.0.113.0/24', '198.51.100.5'])
    def test_only_listed_addresses_can_reach_it_and_others_see_a_plain_404(self):
        assert self.get('203.0.113.77').status_code == 200            # inside the range
        assert self.get('198.51.100.5').status_code == 200            # exact address
        assert self.get('192.0.2.1').status_code == 404               # anyone else
        assert self.get('203.0.113.77, 192.0.2.1').status_code == 404  # a forged first entry does not help: the real client is the last one

    @override_settings(ADMIN_ALLOWED_IPS=['203.0.113.0/24'])
    def test_the_rest_of_the_site_is_not_affected(self):
        assert Client().get('/healthz', HTTP_X_FORWARDED_FOR='192.0.2.1').status_code in (200, 503)


def test_admin_address_can_be_moved():
    env = {**os.environ, 'USE_SQLITE': 'True', 'DEBUG': 'False', 'SECRET_KEY': get_random_secret_key(), 'ADMIN_URL': 'ops-4f9k2/'}
    code = ('import os, django; os.environ["DJANGO_SETTINGS_MODULE"]="config.settings"; django.setup(); '
            'from django.urls import reverse; print(reverse("admin:index"))')
    r = subprocess.run([sys.executable, '-c', code], cwd=BACKEND, capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == '/ops-4f9k2/'


def test_default_anonymous_limit_is_high_enough_for_real_browsing():
    from django.conf import settings
    count, per = settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['anon'].split('/')
    assert per == 'hour' and int(count) >= 600
    assert settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['login'] == '10/min'      # password guessing stays tightly limited
