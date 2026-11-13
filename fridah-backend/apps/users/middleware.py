import logging
import time

logger = logging.getLogger('django')


class RequestLoggingMiddleware:
    """Logs each request method/path/status/duration. Lightweight, production-safe."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()
        response = self.get_response(request)
        duration_ms = (time.time() - start) * 1000
        if request.path.startswith('/api/'):
            logger.info(
                "%s %s -> %s (%.1fms)",
                request.method, request.get_full_path(), response.status_code, duration_ms
            )
        return response
