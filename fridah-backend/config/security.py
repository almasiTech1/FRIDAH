"""Start-up safety checks that must run before Django finishes loading its settings."""
import sys

from django.core.exceptions import ImproperlyConfigured

PLACEHOLDERS = ('django-insecure', 'change-me', 'changeme', 'change_me', 'your-secret', 'your_secret', 'secret-key-here', 'replace-me', 'example')
MIN_LENGTH = 50          # same bar as Django's own `check --deploy`


def secret_key_problem(key: str) -> str | None:
    """Why this key is unsafe for production, or None if it is fine."""
    if not key:
        return 'it is empty'
    lowered = key.lower()
    if any(p in lowered for p in PLACEHOLDERS):
        return 'it is a placeholder or the public default from the example files'
    if len(key) < MIN_LENGTH:
        return f'it is too short ({len(key)} characters; use at least {MIN_LENGTH})'
    if len(set(key)) < 5:
        return 'it has too few different characters'
    return None


def validate_secret_key(key: str, debug: bool) -> None:
    """
    Refuse to start in production with a guessable SECRET_KEY: the same key signs every login token, so anyone who
    knows it can forge a token for any user, including an admin. Development (DEBUG=True) and test runs are exempt.
    """
    if debug or 'pytest' in sys.modules:
        return
    problem = secret_key_problem(key)
    if problem:
        raise ImproperlyConfigured(
            f'Unsafe SECRET_KEY: {problem}. Set a unique random value in your environment, for example: '
            "python -c \"from django.core.management.utils import get_random_secret_key as g; print(g())\""
        )
