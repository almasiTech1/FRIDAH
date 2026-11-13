from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone

from apps.users.permissions import IsServiceProvider, IsAdminRole, IsLandlordOrAdmin
from .models import ServiceCategory, ServiceJob, Quote, ServiceProviderProfile, JobReview
from .serializers import (
    ServiceCategorySerializer, ServiceJobSerializer, QuoteSerializer,
    ServiceProviderProfileSerializer, JobReviewSerializer, PublicServiceProviderSerializer,
)


def success(data=None, message="OK", status_code=status.HTTP_200_OK):
    return Response({'success': True, 'message': message, 'data': data}, status=status_code)


class ServiceCategoryListView(generics.ListCreateAPIView):
    serializer_class = ServiceCategorySerializer
    queryset = ServiceCategory.objects.all().order_by('name')

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminRole()]
        return [permissions.AllowAny()]


class ServiceJobListCreateView(generics.ListCreateAPIView):
    serializer_class = ServiceJobSerializer
    filterset_fields = ['status', 'category', 'county', 'town']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'service_provider':
            # providers see open jobs in their categories/area + jobs assigned to them
            return ServiceJob.objects.filter(
                models_q_open_or_assigned(user)
            ).order_by('-created_at')
        if user.role == 'admin':
            return ServiceJob.objects.all().order_by('-created_at')
        return ServiceJob.objects.filter(posted_by=user).order_by('-created_at')


def models_q_open_or_assigned(user):
    from django.db.models import Q
    return Q(status=ServiceJob.Status.OPEN) | Q(assigned_provider=user)


class ServiceJobDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = ServiceJobSerializer
    queryset = ServiceJob.objects.all()
    lookup_field = 'id'


class QuoteCreateView(generics.CreateAPIView):
    serializer_class = QuoteSerializer
    permission_classes = [IsServiceProvider]

    def perform_create(self, serializer):
        quote = serializer.save()
        quote.job.status = ServiceJob.Status.QUOTED
        quote.job.save(update_fields=['status'])


class QuoteAcceptView(APIView):
    permission_classes = [IsLandlordOrAdmin]

    def post(self, request, id):
        quote = generics.get_object_or_404(Quote, id=id)
        quote.status = Quote.Status.ACCEPTED
        quote.save(update_fields=['status'])

        job = quote.job
        job.assigned_provider = quote.provider
        job.status = ServiceJob.Status.ASSIGNED
        job.save(update_fields=['assigned_provider', 'status'])

        Quote.objects.filter(job=job).exclude(id=quote.id).update(status=Quote.Status.REJECTED)
        return success(message="Quote accepted. Provider assigned to job.")


class JobStartView(APIView):
    permission_classes = [IsServiceProvider]

    def post(self, request, id):
        job = generics.get_object_or_404(ServiceJob, id=id, assigned_provider=request.user)
        job.status = ServiceJob.Status.IN_PROGRESS
        job.save(update_fields=['status'])
        return success(message="Job marked in progress.")


class JobCompleteView(APIView):
    permission_classes = [IsServiceProvider]

    def post(self, request, id):
        job = generics.get_object_or_404(ServiceJob, id=id, assigned_provider=request.user)
        job.status = ServiceJob.Status.COMPLETED
        job.completed_at = timezone.now()
        job.save(update_fields=['status', 'completed_at'])
        return success(message="Job marked complete.")


class JobReviewCreateView(generics.CreateAPIView):
    serializer_class = JobReviewSerializer


class ServiceProviderProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ServiceProviderProfileSerializer
    permission_classes = [IsServiceProvider]

    def get_object(self):
        profile, _ = ServiceProviderProfile.objects.get_or_create(user=self.request.user)
        return profile


class ServiceProviderListView(generics.ListAPIView):
    """Public/landlord browse of providers (e.g. to invite directly)."""
    serializer_class = ServiceProviderProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['is_available']
    queryset = ServiceProviderProfile.objects.filter(is_available=True)


class PublicServiceProviderListView(generics.ListAPIView):
    """
    Truly public marketplace browse for the marketing site - unauthenticated visitors
    can see verified providers to gauge platform quality before registering, without
    exposing contact details (see PublicServiceProviderSerializer).
    """
    serializer_class = PublicServiceProviderSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = ['is_available']
    queryset = ServiceProviderProfile.objects.filter(is_available=True).select_related('user')
