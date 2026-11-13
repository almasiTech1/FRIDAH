from rest_framework import generics
from apps.users.permissions import IsAdminRole
from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogListView(generics.ListAPIView):
    """Platform admins can browse the full audit trail, optionally filtered by property, action or target."""
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminRole]
    filterset_fields = ['action', 'property', 'target_type', 'severity']

    def get_queryset(self):
        return AuditLog.objects.all()


class PropertyAuditLogListView(generics.ListAPIView):
    """A property owner (or admin) can see the audit trail for just their property."""
    serializer_class = AuditLogSerializer

    def get_queryset(self):
        from apps.properties.models import Property
        from django.shortcuts import get_object_or_404
        from apps.agencies.permissions import user_can_access_property

        property = get_object_or_404(Property, id=self.kwargs['property_id'])
        if not user_can_access_property(self.request.user, property):
            return AuditLog.objects.none()
        return AuditLog.objects.filter(property=property)
