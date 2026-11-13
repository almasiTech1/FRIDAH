import json
import logging
from datetime import timedelta

from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.users.permissions import IsLandlordOrAdmin, IsAdminRole

from .client import AIUnavailableError
from .serializers import (
    PropertySearchQuerySerializer, RentEstimateRequestSerializer,
    ListingGenerateFactsSerializer, MaintenanceTriageRequestSerializer,
)

logger = logging.getLogger('apps.ai')

MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8MB per image, matches Claude's per-image limit with headroom
MAX_IMAGES_PER_LISTING = 6


def success(data=None, message="OK", status_code=status.HTTP_200_OK):
    return Response({'success': True, 'message': message, 'data': data}, status=status_code)


def _ai_unavailable_response():
    return Response(
        {'success': False, 'error': {'message': 'AI features are not configured on this server yet.'}},
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


class PropertyAssistantSearchView(APIView):
    """Natural-language property search: 'Find me a 2-bedroom under KSh 30,000 near Kenyatta University.'"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PropertySearchQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from .property_assistant import run_assistant_search
        try:
            result = run_assistant_search(
                serializer.validated_data['query'],
                user=request.user if request.user.is_authenticated else None,
            )
        except AIUnavailableError:
            return _ai_unavailable_response()
        except Exception as e:
            logger.error("Property assistant search failed: %s", e)
            return Response(
                {'success': False, 'error': {'message': 'Search failed. Please try again.'}}, status=502,
            )
        return success(result)


class RentEstimatorView(APIView):
    """Landlord-facing: recommended rent, occupancy likelihood, and demand notes grounded in real comparables."""
    permission_classes = [IsLandlordOrAdmin]

    def post(self, request):
        serializer = RentEstimateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from .rent_estimator import estimate_rent
        try:
            result = estimate_rent(
                county=data['county'], town=data.get('town', ''), bedrooms=data['bedrooms'],
                amenities=data.get('amenities', []), size_sqm=data.get('size_sqm'), user=request.user,
            )
        except AIUnavailableError:
            return _ai_unavailable_response()
        except Exception as e:
            logger.error("Rent estimation failed: %s", e)
            return Response(
                {'success': False, 'error': {'message': 'Estimation failed. Please try again.'}}, status=502,
            )
        return success(result)


class ListingGeneratorView(APIView):
    """Landlord/hotel-owner-facing: upload photos + facts, get back title/description/amenities/SEO keywords."""
    permission_classes = [IsLandlordOrAdmin]

    def post(self, request):
        images = request.FILES.getlist('images')
        if not images:
            return Response({'success': False, 'error': {'message': 'At least one photo is required.'}}, status=400)
        if len(images) > MAX_IMAGES_PER_LISTING:
            return Response(
                {'success': False, 'error': {'message': f'Maximum {MAX_IMAGES_PER_LISTING} photos allowed.'}},
                status=400,
            )

        try:
            facts_raw = json.loads(request.data.get('facts', '{}'))
        except json.JSONDecodeError:
            return Response({'success': False, 'error': {'message': 'Invalid facts payload.'}}, status=400)

        facts_serializer = ListingGenerateFactsSerializer(data=facts_raw)
        facts_serializer.is_valid(raise_exception=True)

        image_payload = []
        for f in images:
            if f.size > MAX_IMAGE_BYTES:
                return Response(
                    {'success': False, 'error': {'message': f'"{f.name}" is too large (max 8MB per photo).'}},
                    status=400,
                )
            content_type = f.content_type or 'image/jpeg'
            if not content_type.startswith('image/'):
                return Response({'success': False, 'error': {'message': f'"{f.name}" is not an image.'}}, status=400)
            image_payload.append((f.read(), content_type))

        from .listing_generator import generate_listing_copy
        try:
            result = generate_listing_copy(
                images=image_payload, facts=facts_serializer.validated_data, user=request.user,
            )
        except AIUnavailableError:
            return _ai_unavailable_response()
        except Exception as e:
            logger.error("Listing generation failed: %s", e)
            return Response(
                {'success': False, 'error': {'message': 'Generation failed. Please try again.'}}, status=502,
            )
        return success(result)


class MaintenanceTriageView(APIView):
    """
    Tenant-facing: upload a photo of an issue, get back a suggested category/priority. This is an
    assist step only - the tenant/landlord still confirms before a MaintenanceRequest is created,
    it does not autonomously create or assign anything.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        image = request.FILES.get('image')
        if not image:
            return Response({'success': False, 'error': {'message': 'A photo is required.'}}, status=400)
        if image.size > MAX_IMAGE_BYTES:
            return Response({'success': False, 'error': {'message': 'Photo is too large (max 8MB).'}}, status=400)
        content_type = image.content_type or 'image/jpeg'
        if not content_type.startswith('image/'):
            return Response({'success': False, 'error': {'message': 'File is not an image.'}}, status=400)

        serializer = MaintenanceTriageRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from .maintenance_triage import triage_photo, suggest_provider_category
        try:
            result = triage_photo(
                image_bytes=image.read(), media_type=content_type,
                tenant_description=serializer.validated_data.get('description', ''), user=request.user,
            )
            suggested_category = suggest_provider_category(result.get('category', ''))
            result['suggested_service_category'] = (
                {'id': str(suggested_category.id), 'name': suggested_category.name} if suggested_category else None
            )
        except AIUnavailableError:
            return _ai_unavailable_response()
        except Exception as e:
            logger.error("Maintenance triage failed: %s", e)
            return Response(
                {'success': False, 'error': {'message': 'Triage failed. Please describe the issue manually.'}},
                status=502,
            )
        return success(result)


class AIUsageDashboardView(APIView):
    """
    Admin-only visibility into AI feature usage and reliability - the piece flagged
    as missing in the AI/Analytics architecture review: AIInteractionLog already
    captures tokens/latency/success per call, but nothing surfaced it anywhere.

    Deliberately reports token counts and call volume rather than a dollar cost
    estimate: Anthropic's per-model pricing can change, and hardcoding a $/token
    table here would go stale silently. If you want a cost figure, multiply the
    per-model token totals below by your current rate card.
    """
    permission_classes = [IsAdminRole]

    def get(self, request):
        from django.db.models import Count, Sum, Avg, Q
        from .models import AIInteractionLog

        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)
        logs = AIInteractionLog.objects.filter(created_at__gte=since)

        by_feature = list(
            logs.values('feature')
            .annotate(
                calls=Count('id'),
                failures=Count('id', filter=Q(succeeded=False)),
                input_tokens=Sum('input_tokens'),
                output_tokens=Sum('output_tokens'),
                avg_latency_ms=Avg('latency_ms'),
            )
            .order_by('-calls')
        )
        for row in by_feature:
            row['input_tokens'] = row['input_tokens'] or 0
            row['output_tokens'] = row['output_tokens'] or 0
            row['avg_latency_ms'] = round(row['avg_latency_ms'] or 0)
            row['success_rate'] = round((1 - row['failures'] / row['calls']) * 100, 1) if row['calls'] else 100

        by_model = list(
            logs.values('model')
            .annotate(calls=Count('id'), input_tokens=Sum('input_tokens'), output_tokens=Sum('output_tokens'))
            .order_by('-calls')
        )

        total_calls = logs.count()
        total_failures = logs.filter(succeeded=False).count()
        recent_failures = list(
            logs.filter(succeeded=False).order_by('-created_at')[:10]
            .values('feature', 'model', 'error_message', 'created_at')
        )

        return success({
            'period_days': days,
            'summary': {
                'total_calls': total_calls,
                'total_failures': total_failures,
                'success_rate': round((1 - total_failures / total_calls) * 100, 1) if total_calls else 100,
                'total_input_tokens': sum(r['input_tokens'] for r in by_feature),
                'total_output_tokens': sum(r['output_tokens'] for r in by_feature),
            },
            'by_feature': by_feature,
            'by_model': by_model,
            'recent_failures': [
                {**f, 'created_at': f['created_at'].isoformat()} for f in recent_failures
            ],
        })


class LeaseDraftingView(APIView):
    """
    Landlord/agency-facing: draft a residential tenancy agreement grounded in an
    existing Lease row's real terms (rent, deposit, dates, parties). Permission
    mirrors the rest of the platform's property-relationship checks - the caller
    must have a legitimate relationship to the lease's property (owning landlord,
    admin, or agency staff with access to that property).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from apps.rentals.models import Lease
        from apps.agencies.permissions import user_can_access_property

        lease_id = request.data.get('lease_id')
        if not lease_id:
            return Response({'success': False, 'error': {'message': 'lease_id is required.'}}, status=400)
        lease = generics.get_object_or_404(Lease, id=lease_id)

        if not user_can_access_property(request.user, lease.unit.property, required_permission='tenants.manage'):
            return Response({'success': False, 'error': {'message': 'You cannot draft an agreement for this lease.'}}, status=403)

        special_terms = request.data.get('special_terms', '')

        from .lease_drafting import draft_lease_agreement
        try:
            result = draft_lease_agreement(lease, special_terms=special_terms, user=request.user)
        except AIUnavailableError:
            return _ai_unavailable_response()
        return Response({'success': True, 'data': result})
