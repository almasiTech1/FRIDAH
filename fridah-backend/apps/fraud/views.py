from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.users.permissions import IsAdminRole
from .models import FraudFlag
from .serializers import FraudFlagSerializer, FraudFlagReviewSerializer


def success(data=None, message="OK", status_code=200):
    return Response({'success': True, 'message': message, 'data': data}, status=status_code)


class FraudFlagListView(generics.ListAPIView):
    """Admin-only queue of open/reviewed fraud flags."""
    serializer_class = FraudFlagSerializer
    permission_classes = [IsAdminRole]
    filterset_fields = ['flag_type', 'status', 'subject_type']

    def get_queryset(self):
        return FraudFlag.objects.all().order_by('-created_at')


class FraudFlagReviewView(APIView):
    """Admin marks a flag confirmed or dismissed after investigating."""
    permission_classes = [IsAdminRole]

    def post(self, request, id):
        from django.utils import timezone

        flag = generics.get_object_or_404(FraudFlag, id=id)
        serializer = FraudFlagReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        flag.status = serializer.validated_data['status']
        flag.review_notes = serializer.validated_data.get('review_notes', '')
        flag.reviewed_by = request.user
        flag.reviewed_at = timezone.now()
        flag.save(update_fields=['status', 'review_notes', 'reviewed_by', 'reviewed_at'])
        return success(FraudFlagSerializer(flag).data, message="Flag reviewed.")


class RunFraudDetectionView(APIView):
    """Admin manually triggers a detection sweep on demand, outside the nightly schedule."""
    permission_classes = [IsAdminRole]

    def post(self, request):
        from .services import run_all_detections
        results = run_all_detections()
        return success(results, message="Fraud detection sweep complete.")
