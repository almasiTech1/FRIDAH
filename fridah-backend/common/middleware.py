import ipaddress

from django.conf import settings
from django.http import Http404

from apps.payments.security import get_client_ip


class AdminIPAllowlistMiddleware:
    """
    Optionally limit the Django admin site to office / VPN addresses (ADMIN_ALLOWED_IPS, comma separated, CIDR ranges
    allowed). Everyone else gets an ordinary 404, so the page does not even look like it exists. Empty = no limit.
    The client address is the same trusted-proxy-aware one the payment and rate-limit checks use.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        allowed = getattr(settings, 'ADMIN_ALLOWED_IPS', [])
        prefix = '/' + settings.ADMIN_URL
        if allowed and request.path.startswith(prefix) and not self._permitted(get_client_ip(request), allowed):
            raise Http404()
        return self.get_response(request)

    @staticmethod
    def _permitted(ip, allowed) -> bool:
        try:
            addr = ipaddress.ip_address((ip or '').strip())
        except ValueError:
            return False
        for entry in allowed:
            try:
                if addr in ipaddress.ip_network(entry.strip(), strict=False):
                    return True
            except ValueError:
                continue
        return False
