from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.agencies import services as agency_services
from apps.agencies import tasks as statement_tasks
from apps.agencies.models import OwnerStatement
from apps.notifications.models import Notification
from apps.payments.models import Payment
from apps.rentals.models import Invoice
from apps.tax import services as tax_services
from apps.tax.models import TaxType, TaxRule, TaxRecord, TaxAdjustment

JAN = (date(2026, 1, 1), date(2026, 1, 31))


@pytest.fixture
def live_property(property_):
    property_.review_state = property_.ReviewState.APPROVED
    property_.status = property_.Status.ACTIVE
    property_.save()
    return property_


@pytest.fixture
def paid_rent(live_property, tenant, lease):
    invoice = Invoice.objects.create(
        lease=lease, tenant=tenant, invoice_type='rent', amount=Decimal('20000'),
        period_start=date(2026, 1, 1), period_end=date(2026, 1, 31), due_date=date(2026, 1, 5),
    )
    Payment.objects.create(
        payer=tenant, invoice=invoice, amount=Decimal('20000'), method=Payment.Method.MPESA_STK,
        status=Payment.Status.COMPLETED, completed_at=timezone.make_aware(timezone.datetime(2026, 1, 10)),
        reference='TESTPAY-SCHED-1',
    )
    return invoice


# ------------------------------------------------------------------ scheduled statements
@pytest.mark.django_db
class TestScheduledStatements:
    def test_periods_due(self):
        assert [p[0] for p in statement_tasks.periods_due(date(2026, 2, 15))] == ['monthly']
        due = statement_tasks.periods_due(date(2027, 1, 10))
        assert [p[0] for p in due] == ['monthly', 'annual']
        assert due[0][1:] == (date(2026, 12, 1), date(2026, 12, 31))
        assert due[1][1:] == (date(2026, 1, 1), date(2026, 12, 31))

    def test_self_managed_property_is_issued_to_owner_once(self, landlord, live_property, paid_rent):
        first = statement_tasks.generate_for_period(*JAN)
        assert first['generated'] == 1 and first['issued'] == 1 and first['failed'] == 0
        st = OwnerStatement.objects.get(property=live_property)
        assert st.status == OwnerStatement.Status.ISSUED
        assert st.gross_rent_collected == Decimal('20000')
        sent = Notification.objects.filter(user=landlord, title='Owner Statement Ready').count()
        assert sent == 1
        # Re-running (daily beat, retry, admin re-run) must not duplicate anything.
        second = statement_tasks.generate_for_period(*JAN)
        assert second['generated'] == 0 and second['skipped'] == 1
        assert OwnerStatement.objects.filter(property=live_property).count() == 1
        assert Notification.objects.filter(user=landlord, title='Owner Statement Ready').count() == 1

    def test_agency_managed_statement_stays_draft_and_hidden_from_owner(
            self, api_client, landlord, live_property, paid_rent):
        agency = agency_services.create_agency(name='Prime PM', created_by=landlord, email='ops@prime.co.ke')
        agency_services.assign_property_to_agency(
            property=live_property, agency=agency, start_date=date(2025, 1, 1),
            management_fee_percent=Decimal('10'), approved_by=landlord,
        )
        summary = statement_tasks.generate_for_period(*JAN)
        assert summary['left_for_agency_review'] == 1 and summary['issued'] == 0
        st = OwnerStatement.objects.get(property=live_property)
        assert st.status == OwnerStatement.Status.DRAFT
        assert st.agency_commission == Decimal('2000.00')

    def test_owner_never_sees_draft_but_sees_issued(self, api_client, tenant, landlord, live_property, paid_rent):
        from apps.users.models import User
        agency_owner = User.objects.create_user(
            username='agy', email='agy@test.com', password='StrongPass123!', role='landlord', phone_number='+254700000055')
        agency = agency_services.create_agency(name='Prime PM', created_by=agency_owner, email='ops@prime.co.ke')
        agency_services.assign_property_to_agency(
            property=live_property, agency=agency, start_date=date(2025, 1, 1),
            management_fee_percent=Decimal('10'), approved_by=landlord,
        )
        statement_tasks.generate_for_period(*JAN)
        st = OwnerStatement.objects.get(property=live_property)

        api_client.force_authenticate(user=landlord)
        from django.urls import reverse, NoReverseMatch
        # Draft: not retrievable by the owner by id.
        for name in ('owner_statement_detail', 'statement_detail'):
            try:
                url = reverse(name, kwargs={'id': st.id})
                break
            except NoReverseMatch:
                url = None
        assert url, 'statement detail route not found'
        assert api_client.get(url).status_code == 404
        agency_services.issue_statement(st, issued_by=agency_owner)
        assert api_client.get(url).status_code == 200

    def test_one_failing_property_does_not_stop_the_rest(self, monkeypatch, landlord, live_property, paid_rent):
        from apps.properties.models import Property
        from apps.agencies import services
        other = Property.objects.create(landlord=landlord, name='Other', property_type='apartment',
                                        county='Nairobi', town='Kilimani', status='active')  # trusted ORM row
        real = services.generate_owner_statement

        def flaky(*, property, **kw):
            if property.id == other.id:
                raise RuntimeError('boom')
            return real(property=property, **kw)

        monkeypatch.setattr(services, 'generate_owner_statement', flaky)
        summary = statement_tasks.generate_for_period(*JAN)
        assert summary['failed'] == 1 and summary['generated'] == 1

    def test_unpublished_properties_are_skipped(self, property_):
        assert property_.status == 'pending_approval'
        assert statement_tasks.generate_for_period(*JAN)['generated'] == 0


# ------------------------------------------------------------------ tax
@pytest.fixture
def rental_tax(db, admin_user):
    t = TaxType.objects.create(code='rental-income', name='Rental income tax')
    TaxRule.objects.create(tax_type=t, version=1, method='percent_of_gross', rate=Decimal('10'),
                           effective_from=date(2026, 1, 1), effective_to=date(2026, 6, 30), created_by=admin_user)
    TaxRule.objects.create(tax_type=t, version=2, method='percent_of_gross', rate=Decimal('15'),
                           effective_from=date(2026, 7, 1), created_by=admin_user)
    return t


@pytest.fixture
def issued_statement(landlord, live_property, paid_rent):
    statement_tasks.generate_for_period(*JAN)
    return OwnerStatement.objects.get(property=live_property)


@pytest.mark.django_db
class TestTax:
    def test_no_rule_configured_is_refused_not_guessed(self, issued_statement):
        t = TaxType.objects.create(code='vat', name='VAT')
        with pytest.raises(ValidationError, match='No active'):
            tax_services.estimate_for_statement(issued_statement, t)

    def test_rules_are_effective_dated_and_versioned(self, rental_tax):
        assert tax_services.rule_for(rental_tax, date(2026, 3, 31)).version == 1
        assert tax_services.rule_for(rental_tax, date(2026, 7, 1)).version == 2
        assert tax_services.rule_for(rental_tax, date(2025, 12, 31)) is None

    def test_estimate_is_labelled_and_reproducible(self, rental_tax, issued_statement):
        rec = tax_services.estimate_for_statement(issued_statement, rental_tax)
        assert rec.status == TaxRecord.Status.ESTIMATED and rec.is_estimate
        assert rec.calculated_amount == Decimal('2000.00')       # 10% of 20,000 under rule v1
        assert rec.rule.version == 1
        assert 'ESTIMATE' in rec.calculation_breakdown['label']
        assert any('20000.00 x 10.0000% = 2000.00' in s for s in rec.calculation_breakdown['steps'])
        again = tax_services.estimate_for_statement(issued_statement, rental_tax)
        assert again.id == rec.id and TaxRecord.objects.count() == 1

    def test_threshold_and_net_method(self, rental_tax):
        rule = TaxRule.objects.create(tax_type=rental_tax, version=3, method='percent_of_net', rate=Decimal('10'),
                                      annual_threshold=Decimal('5000'), effective_from=date(2030, 1, 1))
        assert tax_services.compute(rule, Decimal('4000'))['calculated_amount'] == Decimal('0.00')
        r = tax_services.compute(rule, Decimal('20000'), Decimal('5000'))
        assert r['taxable_base'] == Decimal('15000.00') and r['calculated_amount'] == Decimal('1500.00')

    def test_adjustment_needs_reason_and_keeps_history(self, rental_tax, issued_statement, admin_user):
        rec = tax_services.estimate_for_statement(issued_statement, rental_tax)
        with pytest.raises(ValidationError):
            tax_services.adjust_record(rec, admin_user, '  ', amount_paid='100')
        rec = tax_services.adjust_record(rec, admin_user, 'KRA assessment received', status='assessed',
                                         calculated_amount='2100', reference='PRN123')
        assert rec.status == 'assessed' and rec.calculated_amount == Decimal('2100.00')
        adj = TaxAdjustment.objects.get(record=rec)
        assert adj.before['calculated_amount'] == '2000.00' and adj.after['calculated_amount'] == '2100.00'
        # assessed records can no longer be silently overwritten by a re-estimate
        with pytest.raises(ValidationError):
            tax_services.estimate_for_statement(issued_statement, rental_tax)

    def test_api_scoping_and_permissions(self, api_client, rental_tax, issued_statement, landlord, stranger, admin_user):
        rec = tax_services.estimate_for_statement(issued_statement, rental_tax)
        api_client.force_authenticate(user=landlord)
        assert api_client.get(f'/api/v1/tax/records/{rec.id}/').status_code == 200
        assert api_client.get('/api/v1/tax/records/').data['results'][0]['label'].startswith('ESTIMATE ONLY')
        # owners cannot change calculated figures, only record a payment
        r = api_client.post(f'/api/v1/tax/records/{rec.id}/adjust/',
                            {'reason': 'x', 'calculated_amount': '1'}, format='json')
        assert r.status_code == 403
        r = api_client.post(f'/api/v1/tax/records/{rec.id}/adjust/',
                            {'reason': 'Paid via iTax', 'amount_paid': '2000', 'status': 'paid', 'reference': 'PRN9'},
                            format='json')
        assert r.status_code == 200 and r.data['data']['status'] == 'paid'
        # other users cannot see it; non-admins cannot create rules
        api_client.force_authenticate(user=stranger)
        assert api_client.get(f'/api/v1/tax/records/{rec.id}/').status_code == 404
        assert api_client.post('/api/v1/tax/rules/', {}, format='json').status_code == 403
        api_client.force_authenticate(user=admin_user)
        assert api_client.get(f'/api/v1/tax/records/{rec.id}/').status_code == 200

    def test_admin_creates_new_rule_version_without_touching_old(self, api_client, rental_tax, admin_user):
        api_client.force_authenticate(user=admin_user)
        r = api_client.post('/api/v1/tax/rules/', {
            'tax_type': str(rental_tax.id), 'method': 'percent_of_gross', 'rate': '12.5',
            'effective_from': '2027-01-01', 'source_reference': 'Finance Act (to confirm)',
        }, format='json')
        assert r.status_code == 201 and r.data['version'] == 3
        assert TaxRule.objects.get(tax_type=rental_tax, version=1).rate == Decimal('10')

    def test_estimate_endpoint_summary_and_csv_export(self, api_client, rental_tax, issued_statement, landlord):
        api_client.force_authenticate(user=landlord)
        r = api_client.post('/api/v1/tax/records/estimate/',
                            {'statement': str(issued_statement.id), 'tax_type': 'rental-income'}, format='json')
        assert r.status_code == 201, r.data
        s = api_client.get('/api/v1/tax/summary/?year=2026').data['data']
        assert s['rows'][0]['calculated'] == Decimal('2000.00') and s['rows'][0]['estimate_only_records'] == 1
        csv_resp = api_client.get('/api/v1/tax/export/?year=2026')
        body = csv_resp.content.decode()
        assert csv_resp['Content-Type'].startswith('text/csv') and 'ESTIMATE' in body
