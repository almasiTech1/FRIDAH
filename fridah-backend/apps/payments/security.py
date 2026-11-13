from django.conf import settings


def get_client_ip(request):
    """
    The address of the caller as seen by OUR infrastructure.

    X-Forwarded-For is a list the client can pre-fill with anything, and each proxy appends the
    address it saw to the END. The first entry is therefore attacker-controlled; the only entries
    we can trust are the ones added by our own proxies. settings.TRUSTED_PROXY_COUNT is the number
    of proxies in front of the app (default 1): the client is the Nth entry from the right.
    0 means no proxy - use the socket address and ignore the header entirely.
    """
    remote = request.META.get('REMOTE_ADDR')
    hops = int(getattr(settings, 'TRUSTED_PROXY_COUNT', 1))
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if hops <= 0 or not forwarded:
        return remote
    parts = [p.strip() for p in forwarded.split(',') if p.strip()]
    if len(parts) < hops:
        return remote
    return parts[-hops]


def is_valid_safaricom_ip(request):
    """
    Validates that an M-Pesa callback genuinely originates from Safaricom's
    published IP ranges. In DEBUG mode this is skipped so local/sandbox testing works.
    """
    if settings.DEBUG:
        return True
    ip = get_client_ip(request)
    return ip in settings.MPESA_ALLOWED_IPS
