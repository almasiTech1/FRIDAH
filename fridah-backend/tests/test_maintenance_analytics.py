from decimal import Decimal
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.rentals.models import MaintenanceRequest
from apps.services.models import ServiceCategory, ServiceJob, Quote
from apps.users.models import User


@pytest.mark.django_db
class TestMaintenanceAnalytics:
    def _request(self, unit, tenant, category='plumbing', priority='medium', status='open', resolved_hours_after=None):
        req = MaintenanceRequest.objects.create(
            tenant=tenant, unit=unit, category=category, title='Issue', description='desc',
            priority=priority, status=status,
        )
        if resolved_hours_after is not None:
            req.resolved_at = req.created_at + timedelta(hours=resolved_hours_after)
            req.status = MaintenanceRequest.Status.RESOLVED
            req.save()
        return req

    def test_landlord_sees_aggregated_stats_for_own_properties(self, api_client, landlord, tenant, unit):
        self._request(unit, tenant, category='plumbing', priority='high', resolved_hours_after=5)
        self._request(unit, tenant, category='electrical', priority='low', status='open')

        api_client.force_authenticate(user=landlord)
        resp = api_client.get('/api/v1/analytics/analytics/maintenance/')
        assert resp.status_code == 200
        data = resp.data['data']
        assert data['total_requests'] == 2
        assert data['open_requests'] == 1
        assert data['avg_response_time_hours'] == 5.0
        assert data['by_status']['resolved'] == 1
        assert data['by_status']['open'] == 1

    def test_cost_per_job_uses_accepted_quotes_only(self, api_client, landlord, tenant, unit):
        req = self._request(unit, tenant, resolved_hours_after=3)
        provider = User.objects.create_user(
            username='provider1', email='provider1@test.com', password='x',
            role='service_provider', phone_number='+254700222001',
        )
        category = ServiceCategory.objects.create(name='Plumbing')
        job = ServiceJob.objects.create(
            posted_by=landlord, category=category, maintenance_request=req,
            title='Fix leak', description='desc', county='Nairobi', town='Westlands',
        )
        Quote.objects.create(job=job, provider=provider, amount=Decimal('3000'), status=Quote.Status.ACCEPTED)
        # a rejected quote from another provider shouldn't count toward the average
        other_provider = User.objects.create_user(
            username='provider2', email='provider2@test.com', password='x',
            role='service_provider', phone_number='+254700222002',
        )
        Quote.objects.create(job=job, provider=other_provider, amount=Decimal('9000'), status=Quote.Status.REJECTED)

        api_client.force_authenticate(user=landlord)
        resp = api_client.get('/api/v1/analytics/analytics/maintenance/')
        data = resp.data['data']
        assert data['jobs_with_accepted_quote'] == 1
        assert Decimal(data['avg_cost_per_job']) == Decimal('3000.00')
        assert Decimal(data['total_cost_this_scope']) == Decimal('3000')

    def test_stranger_landlord_does_not_see_other_landlords_requests(self, api_client, stranger, tenant, unit):
        self._request(unit, tenant)
        other_landlord = User.objects.create_user(
            username='other_landlord3', email='other_landlord3@test.com', password='x',
            role='landlord', phone_number='+254700222003',
        )
        api_client.force_authenticate(user=other_landlord)
        resp = api_client.get('/api/v1/analytics/analytics/maintenance/')
        assert resp.status_code == 200
        assert resp.data['data']['total_requests'] == 0

    def test_top_categories_breakdown(self, api_client, landlord, tenant, unit):
        self._request(unit, tenant, category='plumbing')
        self._request(unit, tenant, category='plumbing')
        self._request(unit, tenant, category='electrical')

        api_client.force_authenticate(user=landlord)
        resp = api_client.get('/api/v1/analytics/analytics/maintenance/')
        categories = {c['category']: c['count'] for c in resp.data['data']['top_categories']}
        assert categories['plumbing'] == 2
        assert categories['electrical'] == 1
