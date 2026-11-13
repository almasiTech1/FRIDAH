import mimetypes

from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from .private_files import read_token


class PrivateFileDownloadView(APIView):
    """
    GET /api/v1/files/private/?t=<signed token>
    The token is the permission: it is only issued by the API for records the caller may see, and it expires
    after a few minutes. Browsers open these links directly, so no Authorization header is expected.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        name = read_token(request.query_params.get('t', ''))
        if not name or not default_storage.exists(name):
            raise Http404()
        content_type = mimetypes.guess_type(name)[0] or 'application/octet-stream'
        response = FileResponse(default_storage.open(name, 'rb'), content_type=content_type)
        response['Content-Disposition'] = 'inline'
        response['X-Content-Type-Options'] = 'nosniff'
        response['Content-Security-Policy'] = "default-src 'none'; sandbox"      # an uploaded file can never run scripts
        response['Cache-Control'] = 'private, no-store'
        return response
