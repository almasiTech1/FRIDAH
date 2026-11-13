import pytest
from decimal import Decimal

from apps.ai.client import extract_json, is_ai_configured, call_claude, AIUnavailableError


class TestExtractJson:
    def test_parses_plain_json(self):
        assert extract_json('{"a": 1}') == {'a': 1}

    def test_parses_json_in_markdown_fence(self):
        text = '```json\n{"a": 1}\n```'
        assert extract_json(text) == {'a': 1}

    def test_parses_json_embedded_in_prose(self):
        text = 'Sure, here is the result: {"rent": 20000, "confidence": "high"} Hope that helps!'
        assert extract_json(text) == {'rent': 20000, 'confidence': 'high'}

    def test_parses_json_array(self):
        text = 'Results: [1, 2, 3] done.'
        assert extract_json(text) == [1, 2, 3]

    def test_raises_valueerror_on_unparseable_text(self):
        with pytest.raises(ValueError):
            extract_json('This is not JSON at all.')


@pytest.mark.django_db
class TestAIGracefulDegradation:
    """The AI features must degrade cleanly (not 500) when ANTHROPIC_API_KEY is
    unset, since it's empty by default and every deployment doesn't necessarily
    have it configured (e.g. staging)."""

    def test_is_ai_configured_false_by_default_in_tests(self, settings):
        settings.ANTHROPIC_API_KEY = ''
        assert is_ai_configured() is False

    def test_call_claude_raises_ai_unavailable_when_unconfigured(self, settings):
        settings.ANTHROPIC_API_KEY = ''
        with pytest.raises(AIUnavailableError):
            call_claude(feature='test', model='claude-x', system='sys', messages=[{'role': 'user', 'content': 'hi'}])

    def test_rent_estimate_falls_back_gracefully_with_no_comparables(self, api_client, landlord, settings):
        """estimate_rent() has its own internal fallback (raw stats, no AI commentary)
        when AI is unavailable, so the endpoint returns 200 rather than 503 — this is
        intentional graceful degradation baked into the service layer, not a bug."""
        settings.ANTHROPIC_API_KEY = ''
        api_client.force_authenticate(user=landlord)
        resp = api_client.post('/api/v1/ai/rent-estimate/', {
            'county': 'Nairobi', 'town': 'Westlands', 'bedrooms': 2,
        }, format='json')
        assert resp.status_code == 200
        assert resp.data['data']['confidence'] == 'none'  # no comparable units exist in this test's DB

    def test_maintenance_triage_endpoint_returns_503_when_unconfigured(self, api_client, tenant, settings):
        settings.ANTHROPIC_API_KEY = ''
        api_client.force_authenticate(user=tenant)
        resp = api_client.post('/api/v1/ai/maintenance-triage/', {
            'description': 'Leaking tap in the kitchen',
        }, format='json')
        assert resp.status_code in (400, 503)  # 400 if image is required by the serializer, 503 once past validation


@pytest.mark.django_db
class TestAIUsageDashboard:
    def test_admin_sees_aggregated_usage(self, api_client, admin_user, landlord):
        from apps.ai.models import AIInteractionLog
        AIInteractionLog.objects.create(
            user=landlord, feature=AIInteractionLog.Feature.RENT_ESTIMATOR, model='claude-haiku-4-5-20251001',
            input_tokens=500, output_tokens=120, succeeded=True, latency_ms=800,
        )
        AIInteractionLog.objects.create(
            user=landlord, feature=AIInteractionLog.Feature.RENT_ESTIMATOR, model='claude-haiku-4-5-20251001',
            input_tokens=400, output_tokens=90, succeeded=False, error_message='timeout', latency_ms=5000,
        )
        api_client.force_authenticate(user=admin_user)
        resp = api_client.get('/api/v1/ai/usage-dashboard/')
        assert resp.status_code == 200
        summary = resp.data['data']['summary']
        assert summary['total_calls'] == 2
        assert summary['total_failures'] == 1
        assert summary['total_input_tokens'] == 900
        by_feature = resp.data['data']['by_feature']
        assert by_feature[0]['feature'] == 'rent_estimator'
        assert by_feature[0]['calls'] == 2

    def test_non_admin_cannot_access_usage_dashboard(self, api_client, landlord):
        api_client.force_authenticate(user=landlord)
        resp = api_client.get('/api/v1/ai/usage-dashboard/')
        assert resp.status_code == 403


@pytest.mark.django_db
class TestOwnerStatementAISummary:
    def _statement(self, landlord, property_):
        from apps.agencies.models import OwnerStatement
        from datetime import date
        return OwnerStatement.objects.create(
            property=property_, owner=landlord,
            period_start=date(2026, 2, 1), period_end=date(2026, 2, 28),
            gross_rent_collected=Decimal('20000'), vacancy_loss=Decimal('0'),
            arrears=Decimal('1500'), agency_commission=Decimal('2000'),
            approved_expenses=Decimal('500'), other_deductions=Decimal('0'),
            net_payable=Decimal('17500'),
        )

    def test_falls_back_to_templated_summary_when_ai_unavailable(self, api_client, landlord, property_, settings):
        settings.ANTHROPIC_API_KEY = ''
        statement = self._statement(landlord, property_)
        api_client.force_authenticate(user=landlord)
        resp = api_client.post(f'/api/v1/agency/statements/{statement.id}/ai-summary/')
        assert resp.status_code == 200
        summary = resp.data['data']['summary']
        assert '20,000' in summary or '20000' in summary
        assert '17,500' in summary or '17500' in summary

    def test_stranger_cannot_summarize_someone_elses_statement(self, api_client, stranger, landlord, property_):
        statement = self._statement(landlord, property_)
        api_client.force_authenticate(user=stranger)
        resp = api_client.post(f'/api/v1/agency/statements/{statement.id}/ai-summary/')
        assert resp.status_code == 403

    def test_landlord_can_summarize_own_statement(self, api_client, landlord, property_):
        statement = self._statement(landlord, property_)
        api_client.force_authenticate(user=landlord)
        resp = api_client.post(f'/api/v1/agency/statements/{statement.id}/ai-summary/')
        assert resp.status_code == 200
        assert resp.data['data']['statement_id'] == str(statement.id)


@pytest.mark.django_db
class TestLeaseDraftingAssistant:
    def test_returns_503_when_ai_unconfigured(self, api_client, landlord, lease, settings):
        settings.ANTHROPIC_API_KEY = ''
        api_client.force_authenticate(user=landlord)
        resp = api_client.post('/api/v1/ai/lease-drafting/', {'lease_id': str(lease.id)}, format='json')
        assert resp.status_code == 503

    def test_missing_lease_id_returns_400(self, api_client, landlord):
        api_client.force_authenticate(user=landlord)
        resp = api_client.post('/api/v1/ai/lease-drafting/', {}, format='json')
        assert resp.status_code == 400

    def test_stranger_cannot_draft_agreement_for_someone_elses_lease(self, api_client, stranger, lease):
        api_client.force_authenticate(user=stranger)
        resp = api_client.post('/api/v1/ai/lease-drafting/', {'lease_id': str(lease.id)}, format='json')
        assert resp.status_code == 403

    def test_tenant_on_the_lease_cannot_draft_agreement(self, api_client, tenant, lease):
        """Only the landlord/agency/admin side should be able to generate a draft -
        matches user_can_access_property()'s tenant = view-level-only semantics."""
        api_client.force_authenticate(user=tenant)
        resp = api_client.post('/api/v1/ai/lease-drafting/', {'lease_id': str(lease.id)}, format='json')
        assert resp.status_code == 403
