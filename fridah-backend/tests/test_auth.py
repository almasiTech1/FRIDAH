import pytest

REGISTER_URL = '/api/v1/auth/register/'
LOGIN_URL = '/api/v1/auth/login/'


@pytest.mark.django_db
class TestRegistration:
    def _payload(self, **overrides):
        payload = {
            'username': 'newuser1', 'email': 'newuser1@test.com',
            'phone_number': '+254700111222',
            'password': 'StrongPass123!', 'password_confirm': 'StrongPass123!',
            'first_name': 'New', 'last_name': 'User', 'role': 'tenant',
        }
        payload.update(overrides)
        return payload

    def test_self_registration_as_tenant_succeeds(self, api_client):
        resp = api_client.post(REGISTER_URL, self._payload(), format='json')
        assert resp.status_code == 201
        assert resp.data['data']['user']['role'] == 'tenant'

    def test_self_registration_as_landlord_succeeds(self, api_client):
        resp = api_client.post(REGISTER_URL, self._payload(role='landlord', email='ll@test.com', username='ll1'), format='json')
        assert resp.status_code == 201
        assert resp.data['data']['user']['role'] == 'landlord'

    def test_cannot_self_register_as_admin(self, api_client):
        """Regression test: role was previously fully attacker-controlled, letting
        anyone register with role="admin" directly through the public signup endpoint."""
        resp = api_client.post(REGISTER_URL, self._payload(role='admin', email='hacker@test.com', username='hacker1'), format='json')
        assert resp.status_code == 400
        assert 'role' in resp.data['error']['details']

    def test_password_mismatch_rejected(self, api_client):
        resp = api_client.post(
            REGISTER_URL,
            self._payload(password_confirm='DifferentPass123!'),
            format='json',
        )
        assert resp.status_code == 400


@pytest.mark.django_db
class TestLogin:
    def test_login_with_correct_credentials(self, api_client, tenant):
        resp = api_client.post(LOGIN_URL, {'email': 'tenant1@test.com', 'password': 'StrongPass123!'}, format='json')
        assert resp.status_code == 200
        assert 'access' in resp.data['data']['tokens']
        assert 'refresh' in resp.data['data']['tokens']

    def test_login_with_wrong_password_rejected(self, api_client, tenant):
        resp = api_client.post(LOGIN_URL, {'email': 'tenant1@test.com', 'password': 'WrongPass!'}, format='json')
        assert resp.status_code == 400
