import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key

from config.security import secret_key_problem, validate_secret_key

BACKEND = Path(__file__).resolve().parent.parent


class TestSecretKeyRules:
    @pytest.mark.parametrize('bad', ['', 'django-insecure-change-me-in-production', 'CHANGE-ME-generate-a-real-random-secret-key',
                                     'short-but-random-ish-9f8a7c', 'a' * 80, 'x7Kq9Zp2' * 3])
    def test_unsafe_keys_are_flagged(self, bad):
        assert secret_key_problem(bad)

    def test_a_generated_key_is_accepted(self):
        assert secret_key_problem(get_random_secret_key()) is None
        assert secret_key_problem(os.urandom(32).hex()) is None

    def test_debug_mode_is_exempt_but_production_refuses(self):
        validate_secret_key('django-insecure-x', debug=True)                       # local development is fine (and tests run under pytest)
        with pytest.raises(ImproperlyConfigured) as e:
            _run_outside_pytest('django-insecure-x')
        assert 'Unsafe SECRET_KEY' in str(e.value)


def _run_outside_pytest(key, debug=False):
    """Run the check in a fresh interpreter (the guard is skipped while pytest is loaded)."""
    code = ('from config.security import validate_secret_key; import sys\n'
            f'validate_secret_key({key!r}, {debug})')
    r = subprocess.run([sys.executable, '-c', code], cwd=BACKEND, capture_output=True, text=True, env={**os.environ, 'DJANGO_SETTINGS_MODULE': ''})
    if r.returncode:
        raise ImproperlyConfigured(r.stderr.strip().splitlines()[-1])


def test_real_settings_refuse_to_boot_with_the_default_key():
    env = {k: v for k, v in os.environ.items() if k not in ('SECRET_KEY', 'DEBUG')}
    r = subprocess.run([sys.executable, '-c', 'import django, os; os.environ["DJANGO_SETTINGS_MODULE"]="config.settings"; from django.conf import settings; settings.SECRET_KEY'],
                       cwd=BACKEND, capture_output=True, text=True, env={**env, 'USE_SQLITE': 'True'})
    assert r.returncode != 0 and 'Unsafe SECRET_KEY' in r.stderr


def test_real_settings_boot_with_a_proper_key():
    env = {**os.environ, 'USE_SQLITE': 'True', 'DEBUG': 'False', 'SECRET_KEY': get_random_secret_key()}
    r = subprocess.run([sys.executable, '-c', 'import os; os.environ["DJANGO_SETTINGS_MODULE"]="config.settings"; from django.conf import settings; print(len(settings.SECRET_KEY))'],
                       cwd=BACKEND, capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr
