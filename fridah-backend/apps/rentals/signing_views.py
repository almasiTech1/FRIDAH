from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from apps.users.views import success
from .models import Lease
from .signing import LeaseSignature, LeaseSignatureView


class LeaseSignatureStatusView(APIView):
    def get(self, request, lease_id):
        lease = generics.get_object_or_404(Lease, id=lease_id)
        try:
            sig = lease.signature
            data = {
                'status': sig.status,
                'tenant_signed_at': str(sig.tenant_signed_at) if sig.tenant_signed_at else None,
                'landlord_signed_at': str(sig.landlord_signed_at) if sig.landlord_signed_at else None,
                'is_complete': sig.status == LeaseSignature.Status.FULLY_SIGNED,
            }
        except LeaseSignature.DoesNotExist:
            data = {'status': 'not_initiated', 'is_complete': False}
        return success(data)


class LeaseInitiateSigningView(APIView):
    def post(self, request, lease_id):
        lease = generics.get_object_or_404(Lease, id=lease_id, landlord=request.user)
        sig = LeaseSignatureView.initiate(lease)
        return success({'status': sig.status}, message="Signing process initiated. Tenant notified via SMS.")


class LeaseSignView(APIView):
    def post(self, request, lease_id):
        lease = generics.get_object_or_404(Lease, id=lease_id)
        ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
        try:
            sig = LeaseSignatureView.sign(lease, request.user, ip)
            return success({'status': sig.status}, message="Lease signed successfully.")
        except (ValueError, PermissionError) as e:
            return Response({'success': False, 'error': {'message': str(e)}}, status=status.HTTP_400_BAD_REQUEST)
