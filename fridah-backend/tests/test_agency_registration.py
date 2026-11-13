"""Agencies are never self-registered: only an administrator registers one, and creates its first admin's login."""
import pytest

from apps.agencies import services
from apps.agencies.models import Agency, AgencyAuditLog, AgencyMembership
from apps.users.models import User

URL = '/api/v1/agencies/'


@pytest.fixture
def admin(admin_user):
    admin_user.role = 'admin'
    admin_user.save()
    return admin_user


def payload(**extra):
    return {'name': 'Prime Property Managers', 'email': 'ops@primepm.co.ke', 'county': 'Nairobi', 'town': 'Westlands',
            'admin_first_name': 'Kamau', 'admin_last_name': 'Mwangi', 'admin_email': 'kamau@primepm.co.ke',
            'admin_phone_number': '+254700000071', **extra}


def make_user(role, n):
    kwargs = {'service_category': 'plumbing'} if role == 'service_provider' else {}
    return User.objects.create_user(username=f'u{n}', email=f'u{n}@test.com', password='StrongPass123!', role=role,
                                    phone_number=f'+2547000001{n:02d}', **kwargs)


@pytest.mark.django_db
class TestNoSelfRegistration:
    @pytest.mark.parametrize('role', ['tenant', 'landlord', 'service_provider', 'hotel_owner'])
    def test_every_non_admin_role_is_refused(self, api_client, role):
        api_client.force_authenticate(user=make_user(role, 1))
        assert api_client.post(URL, payload(), format='json').status_code == 403
        assert not Agency.objects.exists() and not User.objects.filter(email='kamau@primepm.co.ke').exists()

    def test_existing_agency_admin_cannot_register_another_agency(self, api_client, landlord):
        services.create_agency(name='Existing', created_by=landlord, email='a@b.co.ke')
        api_client.force_authenticate(user=landlord)
        assert api_client.post(URL, payload(), format='json').status_code == 403
        assert Agency.objects.count() == 1

    def test_anonymous_is_refused(self, api_client):
        assert api_client.post(URL, payload(), format='json').status_code in (401, 403)

    def test_public_signup_cannot_create_an_agency_account(self, api_client):
        r = api_client.post('/api/v1/auth/register/', {
            'email': 'agency@x.com', 'username': 'agencyx', 'phone_number': '+254700000099', 'role': 'agency',
            'first_name': 'A', 'last_name': 'B', 'password': 'StrongPass123!', 'password_confirm': 'StrongPass123!',
        }, format='json')
        assert r.status_code == 400 and not User.objects.filter(email='agency@x.com').exists()


@pytest.mark.django_db
class TestAdminRegistration:
    def test_admin_registers_agency_and_creates_its_admin_login(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        r = api_client.post(URL, payload(), format='json')
        assert r.status_code == 201, r.data
        agency = Agency.objects.get(name='Prime Property Managers')
        assert agency.status == Agency.Status.ACTIVE and agency.created_by_id == admin.id
        user = User.objects.get(email='kamau@primepm.co.ke')
        assert user.must_change_password and user.is_active and user.get_full_name() == 'Kamau Mwangi'
        m = AgencyMembership.objects.get(agency=agency)
        assert m.user_id == user.id and m.role.role_type == 'agency_admin' and m.status == 'active'
        creds = r.data['data']['credentials']
        assert creds['login_email'] == 'kamau@primepm.co.ke' and len(creds['temporary_password']) >= 12
        assert user.check_password(creds['temporary_password'])
        assert not AgencyMembership.objects.filter(agency=agency, user=admin).exists()
        assert AgencyAuditLog.objects.filter(agency=agency, action='agency.registered_by_admin', actor=admin).exists()
        for secret in ('admin_email', 'admin_phone_number'):
            assert secret not in r.data['data']

    def test_temporary_password_is_never_retrievable_afterwards(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        agency_id = api_client.post(URL, payload(), format='json').data['data']['id']
        got = api_client.get(f'{URL}{agency_id}/')
        assert 'credentials' not in str(got.data) and 'temporary_password' not in str(got.data)
        assert 'temporary_password' not in str(api_client.get(URL).data)

    def test_validation_and_no_partial_records_on_failure(self, api_client, admin, tenant):
        api_client.force_authenticate(user=admin)
        assert api_client.post(URL, payload(admin_email=tenant.email), format='json').status_code == 400   # email taken
        assert api_client.post(URL, payload(admin_phone_number=tenant.phone_number), format='json').status_code == 400
        assert api_client.post(URL, payload(admin_phone_number='0712'), format='json').status_code == 400   # bad format
        bad = payload(); bad.pop('admin_last_name')
        assert api_client.post(URL, bad, format='json').status_code == 400
        assert not Agency.objects.exists()

    def test_new_agency_appears_in_directory(self, api_client, admin, tenant):
        api_client.force_authenticate(user=admin)
        api_client.post(URL, payload(), format='json')
        api_client.force_authenticate(user=tenant)
        assert 'Prime Property Managers' in [a['name'] for a in api_client.get(URL + 'directory/?search=Prime').data]

    def test_admin_can_suspend_and_reactivate(self, api_client, admin, tenant):
        api_client.force_authenticate(user=admin)
        agency_id = api_client.post(URL, payload(), format='json').data['data']['id']
        assert api_client.post(f'{URL}{agency_id}/status/', {'status': 'suspended'}, format='json').status_code == 200
        api_client.force_authenticate(user=tenant)
        assert 'Prime Property Managers' not in [a['name'] for a in api_client.get(URL + 'directory/?search=Prime').data]
        assert api_client.post(f'{URL}{agency_id}/status/', {'status': 'active'}, format='json').status_code == 403
        api_client.force_authenticate(user=admin)
        assert api_client.post(f'{URL}{agency_id}/status/', {'status': 'nonsense'}, format='json').status_code == 400
        assert api_client.post(f'{URL}{agency_id}/status/', {'status': 'active'}, format='json').status_code == 200


@pytest.mark.django_db
class TestTemporaryPasswordLifecycle:
    def _login(self, client, email, password):
        client.force_authenticate(user=None)
        return client.post('/api/v1/auth/login/', {'email': email, 'password': password}, format='json')

    def test_first_login_is_locked_down_until_password_changed(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        creds = api_client.post(URL, payload(), format='json').data['data']['credentials']

        r = self._login(api_client, creds['login_email'], creds['temporary_password'])
        assert r.status_code == 200 and r.data['data']['user']['must_change_password'] is True
        token = r.data['data']['tokens']['access']
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Everything except the profile/password change is refused at the API
        blocked = api_client.get(URL)
        assert blocked.status_code == 403 and 'change your temporary password' in str(blocked.data).lower()
        assert api_client.get('/api/v1/properties/').status_code == 403
        assert api_client.get('/api/v1/me/').status_code == 200

        # Reusing the temporary password is rejected; a new one unlocks the account
        same = api_client.post('/api/v1/auth/change-password/',
                               {'old_password': creds['temporary_password'], 'new_password': creds['temporary_password']}, format='json')
        assert same.status_code == 400
        ok = api_client.post('/api/v1/auth/change-password/',
                             {'old_password': creds['temporary_password'], 'new_password': 'My-New-Passw0rd!'}, format='json')
        assert ok.status_code == 200
        assert api_client.get(URL).status_code == 200
        assert User.objects.get(email=creds['login_email']).must_change_password is False
        assert self._login(api_client, creds['login_email'], creds['temporary_password']).status_code == 400

    def test_admin_can_issue_a_new_temporary_password(self, api_client, admin, tenant):
        api_client.force_authenticate(user=admin)
        data = api_client.post(URL, payload(), format='json').data['data']
        old = data['credentials']['temporary_password']
        r = api_client.post(f"{URL}{data['id']}/reset-admin-password/")
        assert r.status_code == 200 and r.data['data']['temporary_password'] != old
        user = User.objects.get(email='kamau@primepm.co.ke')
        assert user.check_password(r.data['data']['temporary_password']) and not user.check_password(old)
        assert user.must_change_password
        assert AgencyAuditLog.objects.filter(action='agency.admin_password_reset', actor=admin).exists()
        api_client.force_authenticate(user=tenant)
        assert api_client.post(f"{URL}{data['id']}/reset-admin-password/").status_code == 403


@pytest.mark.django_db
class TestAgencyCreatesStaffLogins:
    @pytest.fixture
    def agency_ctx(self, api_client, admin):
        api_client.force_authenticate(user=admin)
        data = api_client.post(URL, payload(), format='json').data['data']
        agency = Agency.objects.get(id=data['id'])
        boss = User.objects.get(email='kamau@primepm.co.ke')
        role = agency.roles.exclude(role_type='agency_admin').first()
        return agency, boss, role

    def invite(self, client, user, agency, role, **body):
        client.force_authenticate(user=user)
        return client.post(f'{URL}{agency.id}/members/invite/', {'role_id': str(role.id), **body}, format='json')

    def test_unknown_email_gets_a_login_created_by_the_agency(self, api_client, agency_ctx):
        agency, boss, role = agency_ctx
        boss.must_change_password = False
        boss.save()
        r = self.invite(api_client, boss, agency, role, email='wanjiku@primepm.co.ke', first_name='Wanjiku',
                        last_name='Njoroge', phone_number='+254700000072')
        assert r.status_code == 201, r.data
        user = User.objects.get(email='wanjiku@primepm.co.ke')
        creds = r.data['data']['credentials']
        assert user.must_change_password and user.check_password(creds['temporary_password'])
        m = AgencyMembership.objects.get(agency=agency, user=user)
        assert m.status == 'active' and m.role_id == role.id
        assert AgencyAuditLog.objects.filter(agency=agency, action='staff.account_created', actor=boss).exists()

    def test_details_required_when_creating_a_login(self, api_client, agency_ctx):
        agency, boss, role = agency_ctx
        boss.must_change_password = False; boss.save()
        r = self.invite(api_client, boss, agency, role, email='new@primepm.co.ke')
        assert r.status_code == 400 and {'first_name', 'last_name', 'phone_number'} <= set(r.data)
        assert not User.objects.filter(email='new@primepm.co.ke').exists()
        r = self.invite(api_client, boss, agency, role, email='new@primepm.co.ke', first_name='A', last_name='B',
                        phone_number='0712')
        assert r.status_code == 400 and not User.objects.filter(email='new@primepm.co.ke').exists()

    def test_existing_account_is_still_invited_not_duplicated(self, api_client, agency_ctx, tenant):
        agency, boss, role = agency_ctx
        boss.must_change_password = False; boss.save()
        r = self.invite(api_client, boss, agency, role, email=tenant.email)
        assert r.status_code == 201 and 'credentials' not in r.data['data']
        assert AgencyMembership.objects.get(agency=agency, user=tenant).status == 'invited'

    def test_only_those_with_manage_staff_can_add_staff(self, api_client, agency_ctx, tenant):
        agency, boss, role = agency_ctx
        r = self.invite(api_client, tenant, agency, role, email='x@y.co.ke', first_name='A', last_name='B',
                        phone_number='+254700000073')
        assert r.status_code == 403 and not User.objects.filter(email='x@y.co.ke').exists()

    def test_staff_login_reset(self, api_client, agency_ctx, tenant, admin):
        agency, boss, role = agency_ctx
        boss.must_change_password = False; boss.save()
        creds = self.invite(api_client, boss, agency, role, email='w@primepm.co.ke', first_name='W', last_name='N',
                            phone_number='+254700000074').data['data']['credentials']
        m = AgencyMembership.objects.get(user__email='w@primepm.co.ke')
        api_client.force_authenticate(user=boss)
        r = api_client.post(f'{URL}memberships/{m.id}/reset-password/')
        assert r.status_code == 200 and r.data['data']['temporary_password'] != creds['temporary_password']
        assert User.objects.get(email='w@primepm.co.ke').check_password(r.data['data']['temporary_password'])
        # an agency admin cannot reset another Agency Admin; only the platform admin can
        boss_m = AgencyMembership.objects.get(agency=agency, user=boss)
        api_client.force_authenticate(user=User.objects.get(email='w@primepm.co.ke'))
        assert api_client.post(f'{URL}memberships/{boss_m.id}/reset-password/').status_code in (400, 403)
        api_client.force_authenticate(user=admin)
        assert api_client.post(f'{URL}memberships/{boss_m.id}/reset-password/').status_code == 200
        api_client.force_authenticate(user=tenant)
        assert api_client.post(f'{URL}memberships/{m.id}/reset-password/').status_code == 403
