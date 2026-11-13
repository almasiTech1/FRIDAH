from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.db import connection
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

# The old drf-yasg config had public=False (login required to view docs) - preserved here.
schema_view = SpectacularAPIView.as_view(permission_classes=[IsAuthenticated])
docs_view = SpectacularSwaggerView.as_view(url_name='schema', permission_classes=[IsAuthenticated])


def healthz(request):
    """
    Unauthenticated liveness/readiness probe for load balancers, uptime monitors, and
    deploy scripts (e.g. to confirm the new container is actually serving before a
    reverse proxy is pointed at it). Checks the DB connection since a backend that's up
    but can't reach Postgres isn't actually healthy.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'detail': str(e)}, status=503)


from common.views import PrivateFileDownloadView

urlpatterns = [
    path('healthz', healthz, name='healthz'),
    path(settings.ADMIN_URL, admin.site.urls),

    path('api/v1/files/private/', PrivateFileDownloadView.as_view(), name='private-file'),
    path('api/v1/', include('apps.users.urls')),
    path('api/v1/', include('apps.properties.urls')),
    path('api/v1/', include('apps.rentals.urls')),
    path('api/v1/', include('apps.bookings.urls')),
    path('api/v1/', include('apps.services.urls')),
    path('api/v1/', include('apps.payments.urls')),
    path('api/v1/', include('apps.notifications.urls')),
    path('api/v1/analytics/', include('apps.analytics.urls')),
    path('api/v1/', include('apps.ussd.urls')),
    path('api/v1/ai/', include('apps.ai.urls')),
    path('api/v1/', include('apps.visitors.urls')),
    path('api/v1/', include('apps.fraud.urls')),
    path('api/v1/', include('apps.agencies.urls')),
    path('api/v1/', include('apps.audit.urls')),
    path('api/v1/', include('apps.tax.urls')),
    path('api/v1/', include('apps.search.urls')),

    path('api/schema/', schema_view, name='schema'),
    path('api/docs/', docs_view, name='api_docs'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
