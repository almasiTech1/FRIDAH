"""When Redis is down, login/OTP attempts are still limited; ordinary traffic keeps working."""
import pytest
from rest_framework.throttling import SimpleRateThrottle


class BrokenCache:
    def get(self, *a, **k): raise ConnectionError('redis is down')
    def set(self, *a, **k): raise ConnectionError('redis is down')
    def get_many(self, *a, **k): raise ConnectionError('redis is down')


@pytest.fixture
def redis_down(monkeypatch):
    monkeypatch.setattr(SimpleRateThrottle, 'cache', BrokenCache())


@pytest.mark.django_db
class TestFallbackLimiter:
    def test_login_guessing_is_still_limited_while_redis_is_down(self, api_client, tenant, redis_down):
        codes = [api_client.post('/api/v1/auth/login/', {'email': tenant.email, 'password': 'wrong'}, format='json').status_code for _ in range(12)]
        assert codes[:10] == [400] * 10          # the first ten guesses are answered normally...
        assert codes[10:] == [429, 429]          # ...then the limit (10/min) kicks in even without Redis

    def test_ordinary_endpoints_stay_available_while_redis_is_down(self, api_client, redis_down):
        assert all(api_client.get('/api/v1/properties/').status_code == 200 for _ in range(5))

    def test_fallback_counts_do_not_leak_between_tests(self, api_client, tenant, redis_down):
        r = api_client.post('/api/v1/auth/login/', {'email': tenant.email, 'password': 'wrong'}, format='json')
        assert r.status_code == 400               # fresh count at the start of every test
