import logging

from django.core.cache.backends.locmem import LocMemCache
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle, ScopedRateThrottle

logger = logging.getLogger('apps.users.throttling')

# Endpoints where brute-forcing is the threat: password guessing, one-time codes, payment prompts.
SENSITIVE_SCOPES = {'login', 'otp', 'mpesa'}
# Used only while the main cache (Redis) is unreachable. It lives inside each server process, so the limit is
# per worker rather than shared, but guessing is still throttled instead of being wide open.
FALLBACK_CACHE = LocMemCache('throttle-fallback', {})


class FailOpenThrottleMixin:
    """
    DRF's throttle classes read/write the configured cache (Redis in production)
    on every single request. If that cache is ever unreachable - a Redis outage,
    a misconfigured REDIS_URL, a network blip - the default behavior is to let
    the exception propagate, which turns into a 500 for every request across the
    whole API, not just a rate-limiting failure.

    Rate limiting is a protective *degradation*, not a core correctness
    requirement: it is far better to temporarily serve requests unthrottled
    during a cache outage than to take the entire platform down because of one.
    These wrappers catch exactly that failure mode and fail open for ordinary traffic. The exception is the
    sensitive scopes (login, otp, mpesa): those fall back to an in-process counter so they are never left unlimited.
    """

    def allow_request(self, request, view):
        try:
            return super().allow_request(request, view)
        except Exception:
            if getattr(self, 'scope', None) in SENSITIVE_SCOPES:
                # Sensitive endpoints must not become unlimited just because Redis is down: count in-process instead.
                logger.error("Throttle cache unavailable (%s, scope=%s) - using the in-process fallback limiter.",
                             self.__class__.__name__, self.scope, exc_info=True)
                return self._allow_with_fallback(request, view)
            logger.error(
                "Throttle cache unavailable (%s) - allowing request through unthrottled.",
                self.__class__.__name__, exc_info=True,
            )
            return True

    def _allow_with_fallback(self, request, view):
        original = self.cache
        self.cache = FALLBACK_CACHE
        try:
            return super().allow_request(request, view)
        except Exception:
            return True                      # never let the fallback itself take the endpoint down
        finally:
            self.cache = original

    def wait(self):
        try:
            return super().wait()
        except Exception:
            return None


class SafeAnonRateThrottle(FailOpenThrottleMixin, AnonRateThrottle):
    pass


class SafeUserRateThrottle(FailOpenThrottleMixin, UserRateThrottle):
    pass


class SafeScopedRateThrottle(FailOpenThrottleMixin, ScopedRateThrottle):
    pass
