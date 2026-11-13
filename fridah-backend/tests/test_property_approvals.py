"""
Dual-approval workflow (report sections 3.3 / 6): an agency-submitted property is
published only when BOTH landlord and administrator have approved the current version.
"""
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.agencies import services as agency_services
from apps.notifications.models import Notification
from apps.properties.models import Property, PropertyApproval, Unit
from apps.users.models import User

URL = '/api/v1/properties/'
PAYLOAD = {
    'name': 'Karen Heights', 'property_type': 'apartment', 'county': 'Nairobi',
    'town': 'Karen', 'address_detail': 'Ngong Rd', 'total_units': 4,
}


@pytest.fixture
def agent(db):
    """Agency staff member (agency admin) who onboards properties for client landlords."""
    user = User.objects.create_user(
        username='agent1', email='agent1@test.com', password='StrongPass123!',
        role='landlord', phone_number='+254700000010',
    )
    agency_services.create_agency(name='Prime PM', created_by=user, email='ops@prime.co.ke')
    return user


@pytest.fixture
def submitted(api_client, agent, landlord):
    """A property an agency submitted on behalf of `landlord`."""
    api_client.force_authenticate(user=agent)
    resp = api_client.post(URL, {**PAYLOAD, 'landlord': str(landlord.id)}, format='json')
    assert resp.status_code == 201, resp.data
    api_client.force_authenticate(user=None)
    return Property.objects.get(name='Karen Heights')


def _review(client, user, prop, action, comment=''):
    client.force_authenticate(user=user)
    resp = client.post(f'{URL}{prop.id}/review/', {'action': action, 'comment': comment}, format='json')
    client.force_authenticate(user=None)
    return resp


def _admin_action(client, admin, prop, action, comment=''):
    client.force_authenticate(user=admin)
    resp = client.post(f'{URL}{prop.id}/approval/', {'action': action, 'comment': comment}, format='json')
    client.force_authenticate(user=None)
    return resp


def _public_ids(client):
    resp = client.get(URL)
    rows = resp.data['results'] if isinstance(resp.data, dict) and 'results' in resp.data else resp.data
    return {str(r['id']) for r in rows}


@pytest.mark.django_db
class TestSubmission:
    def test_agency_submission_requires_both_approvals_and_is_unpublished(self, submitted, agent, landlord):
        assert submitted.status == Property.Status.PENDING_APPROVAL
        assert submitted.requires_landlord_approval is True
        assert submitted.review_state == Property.ReviewState.AWAITING_LANDLORD
        assert submitted.submitted_by_id == agent.id
        assert submitted.submitted_by_agency is not None
        # landlord is told about it
        assert Notification.objects.filter(user=landlord, title__icontains='awaiting your approval').exists()
        # submission is on the immutable trail
        assert submitted.approvals.filter(decision='submitted').count() == 1

    def test_landlord_created_property_needs_admin_only(self, api_client, landlord):
        api_client.force_authenticate(user=landlord)
        resp = api_client.post(URL, PAYLOAD, format='json')
        assert resp.status_code == 201
        prop = Property.objects.get(name='Karen Heights')
        assert prop.requires_landlord_approval is False
        assert prop.review_state == Property.ReviewState.AWAITING_ADMIN
        assert prop.status == Property.Status.PENDING_APPROVAL

    def test_admin_created_property_is_published_immediately(self, api_client, admin_user, landlord):
        admin_user.role = 'admin'
        admin_user.save()
        api_client.force_authenticate(user=admin_user)
        resp = api_client.post(URL, {**PAYLOAD, 'landlord': str(landlord.id)}, format='json')
        assert resp.status_code == 201
        prop = Property.objects.get(name='Karen Heights')
        assert prop.status == Property.Status.ACTIVE
        assert prop.review_state == Property.ReviewState.APPROVED


@pytest.mark.django_db
class TestDualApproval:
    def test_admin_first_then_landlord_publishes(self, api_client, submitted, admin_user, landlord):
        resp = _admin_action(api_client, admin_user, submitted, 'approve')
        assert resp.status_code == 200
        submitted.refresh_from_db()
        # Admin alone must NOT publish an agent-submitted property.
        assert submitted.status == Property.Status.PENDING_APPROVAL
        assert submitted.review_state == Property.ReviewState.AWAITING_LANDLORD
        assert str(submitted.id) not in _public_ids(api_client)

        assert _review(api_client, landlord, submitted, 'approve').status_code == 200
        submitted.refresh_from_db()
        assert submitted.status == Property.Status.ACTIVE
        assert submitted.review_state == Property.ReviewState.APPROVED
        assert str(submitted.id) in _public_ids(api_client)

    def test_landlord_first_then_admin_publishes(self, api_client, submitted, admin_user, landlord):
        assert _review(api_client, landlord, submitted, 'approve').status_code == 200
        submitted.refresh_from_db()
        assert submitted.status == Property.Status.PENDING_APPROVAL
        assert submitted.review_state == Property.ReviewState.AWAITING_ADMIN
        assert str(submitted.id) not in _public_ids(api_client)

        assert _admin_action(api_client, admin_user, submitted, 'approve').status_code == 200
        submitted.refresh_from_db()
        assert submitted.status == Property.Status.ACTIVE

    def test_decision_rows_record_actor_version_and_states(self, api_client, submitted, admin_user, landlord):
        _review(api_client, landlord, submitted, 'approve')
        _admin_action(api_client, admin_user, submitted, 'approve')
        rows = list(submitted.approvals.filter(decision='approved').order_by('created_at'))
        assert [r.party for r in rows] == ['landlord', 'admin']
        assert rows[0].actor_id == landlord.id and rows[1].actor_id == admin_user.id
        assert rows[1].from_state == 'awaiting_admin' and rows[1].to_state == 'approved'
        assert all(r.submission_version == 1 for r in rows)

    def test_stranger_and_tenant_cannot_review(self, api_client, submitted, stranger):
        resp = _review(api_client, stranger, submitted, 'approve')
        # Unapproved property is invisible to strangers, so this is a 404, not a hint it exists.
        assert resp.status_code == 404
        submitted.refresh_from_db()
        assert submitted.review_state == Property.ReviewState.AWAITING_LANDLORD

    def test_submitting_agent_cannot_approve_for_the_landlord(self, api_client, submitted, agent):
        resp = _review(api_client, agent, submitted, 'approve')
        assert resp.status_code == 403
        submitted.refresh_from_db()
        assert submitted.status == Property.Status.PENDING_APPROVAL

    def test_party_comes_from_caller_not_request_body(self, api_client, submitted, landlord):
        api_client.force_authenticate(user=landlord)
        api_client.post(f'{URL}{submitted.id}/review/', {'action': 'approve', 'party': 'admin'}, format='json')
        api_client.force_authenticate(user=None)
        submitted.refresh_from_db()
        assert submitted.review_state == Property.ReviewState.AWAITING_ADMIN  # only the landlord side recorded
        assert submitted.status == Property.Status.PENDING_APPROVAL

    def test_cannot_publish_with_patch_or_save(self, api_client, submitted, agent, landlord):
        for user in (agent, landlord):
            api_client.force_authenticate(user=user)
            api_client.patch(f'{URL}{submitted.id}/', {'status': 'active', 'review_state': 'approved'}, format='json')
        api_client.force_authenticate(user=None)
        submitted.refresh_from_db()
        assert submitted.status == Property.Status.PENDING_APPROVAL
        assert submitted.review_state == Property.ReviewState.AWAITING_LANDLORD
        # And the model itself refuses, so no stray code path can do it either.
        submitted.status = Property.Status.ACTIVE
        with pytest.raises(ValidationError):
            submitted.save()


@pytest.mark.django_db
class TestVisibility:
    def test_unapproved_property_hidden_from_public_everywhere(self, api_client, submitted, tenant):
        unit = Unit.objects.create(property=submitted, unit_number='A1', rent_amount=Decimal('30000'))
        for client_user in (None, tenant):
            api_client.force_authenticate(user=client_user)
            assert str(submitted.id) not in _public_ids(api_client)
            assert api_client.get(f'{URL}{submitted.id}/').status_code == 404
            assert api_client.get(f'{URL}{submitted.id}/units/').status_code == 404
            assert api_client.get(f'/api/v1/units/{unit.id}/').status_code == 404
            assert api_client.get(f'/api/v1/units/{unit.id}/cost-of-living/').status_code == 404
            assert api_client.get(f'{URL}{submitted.id}/reviews/').status_code == 404

    def test_owner_submitter_and_admin_can_still_see_pending(self, api_client, submitted, landlord, agent, admin_user):
        for user in (landlord, agent, admin_user):
            api_client.force_authenticate(user=user)
            assert api_client.get(f'{URL}{submitted.id}/').status_code == 200

    def test_approved_property_visible_to_public(self, api_client, submitted, admin_user, landlord):
        _review(api_client, landlord, submitted, 'approve')
        _admin_action(api_client, admin_user, submitted, 'approve')
        assert api_client.get(f'{URL}{submitted.id}/').status_code == 200


@pytest.mark.django_db
class TestInvalidationAndRework:
    def _publish(self, client, prop, admin, landlord):
        _review(client, landlord, prop, 'approve')
        _admin_action(client, admin, prop, 'approve')
        prop.refresh_from_db()
        assert prop.status == Property.Status.ACTIVE

    def test_material_edit_after_approval_unpublishes_and_requires_reapproval(
            self, api_client, submitted, admin_user, landlord, agent):
        self._publish(api_client, submitted, admin_user, landlord)
        api_client.force_authenticate(user=agent)
        resp = api_client.patch(f'{URL}{submitted.id}/', {'address_detail': 'New location'}, format='json')
        assert resp.status_code == 200
        api_client.force_authenticate(user=None)
        submitted.refresh_from_db()
        assert submitted.submission_version == 2
        assert submitted.status == Property.Status.PENDING_APPROVAL
        assert submitted.review_state == Property.ReviewState.AWAITING_LANDLORD
        assert str(submitted.id) not in _public_ids(api_client)
        assert submitted.approvals.filter(decision='invalidated').exists()
        # Stale v1 approvals do not count: admin alone at v2 is still not enough.
        _admin_action(api_client, admin_user, submitted, 'approve')
        submitted.refresh_from_db()
        assert submitted.status == Property.Status.PENDING_APPROVAL
        _review(api_client, landlord, submitted, 'approve')
        submitted.refresh_from_db()
        assert submitted.status == Property.Status.ACTIVE

    def test_non_material_edit_keeps_listing_live(self, api_client, submitted, admin_user, landlord, agent):
        self._publish(api_client, submitted, admin_user, landlord)
        api_client.force_authenticate(user=agent)
        api_client.patch(f'{URL}{submitted.id}/', {'caretaker_name': 'Wanjiku'}, format='json')
        api_client.force_authenticate(user=None)
        submitted.refresh_from_db()
        assert submitted.submission_version == 1 and submitted.status == Property.Status.ACTIVE

    def test_reject_needs_comment_and_blocks_publication(self, api_client, submitted, admin_user, landlord):
        assert _review(api_client, landlord, submitted, 'reject').status_code == 400
        assert _review(api_client, landlord, submitted, 'reject', 'Wrong estate').status_code == 200
        submitted.refresh_from_db()
        assert submitted.review_state == Property.ReviewState.REJECTED
        assert _admin_action(api_client, admin_user, submitted, 'approve').status_code == 400
        assert submitted.status == Property.Status.PENDING_APPROVAL

    def test_changes_requested_then_resubmit_starts_new_version(
            self, api_client, submitted, admin_user, landlord, agent):
        _review(api_client, landlord, submitted, 'request_changes', 'Add title deed')
        submitted.refresh_from_db()
        assert submitted.review_state == Property.ReviewState.CHANGES_REQUESTED
        api_client.force_authenticate(user=agent)
        assert api_client.post(f'{URL}{submitted.id}/resubmit/', {}, format='json').status_code == 200
        api_client.force_authenticate(user=None)
        submitted.refresh_from_db()
        assert submitted.submission_version == 2
        assert submitted.review_state == Property.ReviewState.AWAITING_LANDLORD

    def test_resubmitting_never_publishes_and_strangers_cannot_resubmit(
            self, api_client, submitted, landlord, stranger):
        _review(api_client, landlord, submitted, 'reject', 'No')
        api_client.force_authenticate(user=stranger)
        assert api_client.post(f'{URL}{submitted.id}/resubmit/', {}, format='json').status_code == 404
        api_client.force_authenticate(user=landlord)
        assert api_client.post(f'{URL}{submitted.id}/resubmit/', {}, format='json').status_code == 200
        submitted.refresh_from_db()
        # New version: the earlier rejection/approvals are stale and both approvals are needed again.
        assert submitted.submission_version == 2
        assert submitted.status == Property.Status.PENDING_APPROVAL
        assert submitted.review_state == Property.ReviewState.AWAITING_LANDLORD

    def test_suspend_and_reinstate_only_for_fully_approved(self, api_client, submitted, admin_user, landlord):
        assert _admin_action(api_client, admin_user, submitted, 'reinstate').status_code == 400
        self._publish(api_client, submitted, admin_user, landlord)
        assert _admin_action(api_client, admin_user, submitted, 'suspend').status_code == 200
        assert api_client.get(f'{URL}{submitted.id}/').status_code == 404
        assert _admin_action(api_client, admin_user, submitted, 'approve').status_code == 200  # reinstates
        submitted.refresh_from_db()
        assert submitted.status == Property.Status.ACTIVE


@pytest.mark.django_db
class TestTrailAndQueue:
    def test_approval_rows_are_immutable(self, submitted):
        row = submitted.approvals.first()
        row.comment = 'tampered'
        with pytest.raises(ValidationError):
            row.save()
        with pytest.raises(ValidationError):
            row.delete()

    def test_history_endpoint_scoped_to_relationship(self, api_client, submitted, landlord, stranger):
        api_client.force_authenticate(user=landlord)
        assert api_client.get(f'{URL}{submitted.id}/approvals/').status_code == 200
        api_client.force_authenticate(user=stranger)
        assert api_client.get(f'{URL}{submitted.id}/approvals/').status_code == 404

    def test_review_queue_for_landlord_and_admin(self, api_client, submitted, landlord, admin_user, stranger):
        api_client.force_authenticate(user=landlord)
        data = api_client.get(f'{URL}review-queue/').data['data']
        assert data['role'] == 'landlord' and data['count'] == 1
        api_client.force_authenticate(user=stranger)
        assert api_client.get(f'{URL}review-queue/').data['data']['count'] == 0
        api_client.force_authenticate(user=admin_user)
        data = api_client.get(f'{URL}review-queue/').data['data']
        assert data['role'] == 'admin' and data['count'] == 1
        # once the landlord approved it leaves the landlord queue
        _review(api_client, landlord, submitted, 'approve')
        api_client.force_authenticate(user=landlord)
        assert api_client.get(f'{URL}review-queue/').data['data']['count'] == 0
