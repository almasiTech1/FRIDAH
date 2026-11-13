from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import User, OTP, UserDevice, TenantBlacklistEntry
from .serializers import (
    RegisterSerializer, LoginSerializer, TokenResponseSerializer, UserSerializer,
    ProfileUpdateSerializer, KYCSubmitSerializer, KYCReviewSerializer,
    OTPRequestSerializer, OTPVerifySerializer, ChangePasswordSerializer,
    TenantBlacklistEntrySerializer, BlacklistTenantResponseSerializer, BlacklistReviewSerializer,
)
from .services import generate_otp, verify_otp
from .permissions import IsAdminRole, IsLandlordOrAdmin


def success(data=None, message="OK", status_code=status.HTTP_200_OK):
    return Response({'success': True, 'message': message, 'data': data}, status=status_code)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        generate_otp(user, OTP.Purpose.REGISTRATION)
        tokens = TokenResponseSerializer.for_user(user)
        return success(
            {'user': UserSerializer(user).data, 'tokens': tokens},
            message="Registration successful. An OTP has been sent to your phone.",
            status_code=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'login'

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        tokens = TokenResponseSerializer.for_user(user)
        return success({'user': UserSerializer(user).data, 'tokens': tokens}, message="Login successful.")


class TokenRefreshView(BaseTokenRefreshView):
    pass


class LogoutView(APIView):
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                from rest_framework_simplejwt.tokens import RefreshToken
                RefreshToken(refresh_token).blacklist()
        except Exception:
            pass
        return success(message="Logged out successfully.")


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success(UserSerializer(request.user).data, message="Profile updated.")


class OTPRequestView(APIView):
    throttle_scope = 'otp'

    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        generate_otp(request.user, serializer.validated_data['purpose'])
        return success(message="OTP sent.")


class OTPVerifyView(APIView):
    throttle_scope = 'otp'

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ok, msg = verify_otp(request.user, serializer.validated_data['code'], serializer.validated_data['purpose'])
        if not ok:
            return Response({'success': False, 'error': {'message': msg}}, status=status.HTTP_400_BAD_REQUEST)
        if serializer.validated_data['purpose'] == OTP.Purpose.PHONE_VERIFY:
            request.user.is_phone_verified = True
            request.user.save(update_fields=['is_phone_verified'])
        return success(message=msg)


class KYCSubmitView(APIView):
    def post(self, request):
        serializer = KYCSubmitSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success(UserSerializer(request.user).data, message="KYC submitted for review.")


class KYCReviewView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, user_id):
        target = get_object_or_404(User, id=user_id)
        serializer = KYCReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data['action'] == 'approve':
            target.kyc_status = User.KYCStatus.VERIFIED
            target.kyc_rejection_reason = None
        else:
            target.kyc_status = User.KYCStatus.REJECTED
            target.kyc_rejection_reason = serializer.validated_data.get('rejection_reason', '')
        target.kyc_reviewed_at = timezone.now()
        target.kyc_reviewed_by = request.user
        target.save()
        return success(UserSerializer(target).data, message=f"KYC {serializer.validated_data['action']}d.")


class KYCPendingListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAdminRole]
    queryset = User.objects.filter(kyc_status=User.KYCStatus.PENDING)


class ChangePasswordView(APIView):
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.must_change_password = False
        request.user.save()
        return success(message="Password changed successfully.")


class RegisterDeviceView(APIView):
    def post(self, request):
        device_id = request.data.get('device_id')
        fcm_token = request.data.get('fcm_token')
        platform = request.data.get('platform', 'web')
        if not device_id:
            return Response({'success': False, 'error': {'message': 'device_id is required'}}, status=400)
        UserDevice.objects.update_or_create(
            user=request.user, device_id=device_id,
            defaults={'fcm_token': fcm_token, 'platform': platform}
        )
        if fcm_token:
            request.user.fcm_token = fcm_token
            request.user.save(update_fields=['fcm_token'])
        return success(message="Device registered.")


class UserListView(generics.ListAPIView):
    """Admin: list/search users by role, kyc status etc."""
    serializer_class = UserSerializer
    permission_classes = [IsAdminRole]
    filterset_fields = ['role', 'kyc_status', 'county']
    search_fields = ['username', 'email', 'phone_number', 'first_name', 'last_name']
    queryset = User.objects.all().order_by('-created_at')


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAdminRole]
    queryset = User.objects.all()
    lookup_field = 'id'


class TenantBlacklistCreateView(generics.CreateAPIView):
    """A landlord flags a tenant for non-payment or damage. Visible platform-wide once created."""
    serializer_class = TenantBlacklistEntrySerializer
    permission_classes = [IsLandlordOrAdmin]


class TenantBlacklistListView(generics.ListAPIView):
    """
    Landlords see active flags for a specific tenant (e.g. when reviewing an
    application) via ?tenant=<id>. Admins see everything, including disputed/removed,
    for moderation.
    """
    serializer_class = TenantBlacklistEntrySerializer
    filterset_fields = ['tenant', 'status', 'reason']

    def get_queryset(self):
        qs = TenantBlacklistEntry.objects.select_related('tenant', 'flagged_by').order_by('-created_at')
        if self.request.user.role == 'admin':
            return qs
        # Landlords only ever see active flags - disputed/removed entries are a moderation
        # matter between the tenant and platform admins, not something to hold against them.
        return qs.filter(status=TenantBlacklistEntry.Status.ACTIVE)


class TenantBlacklistCheckView(APIView):
    """Quick lookup used on tenant applications: any active flags for this tenant?"""
    def get(self, request, tenant_id):
        entries = TenantBlacklistEntry.objects.filter(
            tenant_id=tenant_id, status=TenantBlacklistEntry.Status.ACTIVE
        ).select_related('flagged_by')
        return success({
            'is_flagged': entries.exists(),
            'flag_count': entries.count(),
            'flags': TenantBlacklistEntrySerializer(entries, many=True).data,
        })


class TenantBlacklistRespondView(APIView):
    """The flagged tenant gives their side of the story; this disputes the flag pending admin review."""
    def post(self, request, id):
        entry = get_object_or_404(TenantBlacklistEntry, id=id, tenant=request.user)
        serializer = BlacklistTenantResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        entry.tenant_response = serializer.validated_data['response']
        entry.tenant_responded_at = timezone.now()
        entry.status = TenantBlacklistEntry.Status.DISPUTED
        entry.save(update_fields=['tenant_response', 'tenant_responded_at', 'status'])
        return success(TenantBlacklistEntrySerializer(entry).data, message="Your response has been recorded for admin review.")


class TenantBlacklistReviewView(APIView):
    """Admin resolves a disputed flag: keep it active or remove it."""
    permission_classes = [IsAdminRole]

    def post(self, request, id):
        entry = get_object_or_404(TenantBlacklistEntry, id=id)
        serializer = BlacklistReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        entry.status = serializer.validated_data['status']
        entry.review_notes = serializer.validated_data.get('review_notes', '')
        entry.reviewed_by = request.user
        entry.reviewed_at = timezone.now()
        entry.save(update_fields=['status', 'review_notes', 'reviewed_by', 'reviewed_at'])
        return success(TenantBlacklistEntrySerializer(entry).data, message="Blacklist entry reviewed.")
