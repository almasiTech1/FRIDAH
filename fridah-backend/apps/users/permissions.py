from rest_framework.permissions import BasePermission


class IsTenant(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'tenant'


class IsLandlord(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'landlord'


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.role == 'admin' or request.user.is_staff)


class IsServiceProvider(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'service_provider'


class IsHotelOwner(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'hotel_owner'


class IsLandlordOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ('landlord', 'admin')


class IsKYCVerified(BasePermission):
    message = "KYC verification required for this action."

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_kyc_verified


class IsOwnerOrReadOnly(BasePermission):
    """Object-level: only the owner field (configurable) can modify."""
    owner_field = 'user'

    def has_object_permission(self, request, view, obj):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        owner = getattr(obj, self.owner_field, None)
        return owner == request.user
