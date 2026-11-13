from decimal import Decimal

import pytest

from apps.fraud import services as fraud_services
from apps.fraud.models import FraudFlag
from apps.properties.models import Property
from apps.payments.models import Payment, MpesaTransaction
from apps.users.models import User


@pytest.mark.django_db
class TestDuplicateListingDetection:
    def test_flags_near_identical_coordinates_different_landlords(self, landlord):
        other_landlord = User.objects.create_user(
            username='other_landlord', email='other_landlord@test.com', password='x',
            role='landlord', phone_number='+254700000005',
        )
        Property.objects.create(
            landlord=landlord, name='Original Listing', property_type='apartment',
            county='Nairobi', town='Westlands', address_detail='123 St',
            latitude=Decimal('-1.2650'), longitude=Decimal('36.8020'), status=Property.Status.ACTIVE,
        )
        Property.objects.create(
            landlord=other_landlord, name='Copied Listing', property_type='apartment',
            county='Nairobi', town='Westlands', address_detail='123 St (copied)',
            latitude=Decimal('-1.2650'), longitude=Decimal('36.8021'), status=Property.Status.ACTIVE,
        )
        created = fraud_services.detect_duplicate_listings()
        assert created == 1
        assert FraudFlag.objects.filter(flag_type=FraudFlag.FlagType.DUPLICATE_LISTING).count() == 1

    def test_does_not_flag_same_landlord_duplicates(self, landlord):
        Property.objects.create(
            landlord=landlord, name='Listing A', property_type='apartment',
            county='Nairobi', town='Westlands', address_detail='123 St',
            latitude=Decimal('-1.2650'), longitude=Decimal('36.8020'), status=Property.Status.ACTIVE,
        )
        Property.objects.create(
            landlord=landlord, name='Listing A resubmitted', property_type='apartment',
            county='Nairobi', town='Westlands', address_detail='123 St',
            latitude=Decimal('-1.2650'), longitude=Decimal('36.8020'), status=Property.Status.ACTIVE,
        )
        created = fraud_services.detect_duplicate_listings()
        assert created == 0

    def test_does_not_flag_distant_properties(self, landlord):
        other_landlord = User.objects.create_user(
            username='other_landlord2', email='other_landlord2@test.com', password='x',
            role='landlord', phone_number='+254700000006',
        )
        Property.objects.create(
            landlord=landlord, name='Nairobi Listing', property_type='apartment',
            county='Nairobi', town='Westlands', address_detail='123 St',
            latitude=Decimal('-1.2650'), longitude=Decimal('36.8020'), status=Property.Status.ACTIVE,
        )
        Property.objects.create(
            landlord=other_landlord, name='Mombasa Listing', property_type='apartment',
            county='Mombasa', town='Nyali', address_detail='456 Rd',
            latitude=Decimal('-4.0500'), longitude=Decimal('39.6700'), status=Property.Status.ACTIVE,
        )
        created = fraud_services.detect_duplicate_listings()
        assert created == 0


@pytest.mark.django_db
class TestSuspiciousPaymentPatternDetection:
    def _failed_mpesa_transaction(self, tenant, phone, i):
        payment = Payment.objects.create(
            payer=tenant, amount=Decimal('1000'), method=Payment.Method.MPESA_STK,
            status=Payment.Status.FAILED, phone_number=phone, reference=f'REF{i}',
        )
        MpesaTransaction.objects.create(payment=payment, phone_number=phone, amount=Decimal('1000'), result_code=1)

    def test_flags_phone_with_many_failed_attempts(self, tenant):
        for i in range(5):
            self._failed_mpesa_transaction(tenant, '+254700999888', i)
        created = fraud_services.detect_suspicious_payment_patterns(failure_threshold=5)
        assert created == 1
        flag = FraudFlag.objects.get(flag_type=FraudFlag.FlagType.SUSPICIOUS_PAYMENT_PATTERN)
        assert flag.subject_id == '+254700999888'

    def test_does_not_flag_below_threshold(self, tenant):
        for i in range(3):
            self._failed_mpesa_transaction(tenant, '+254700999777', i)
        created = fraud_services.detect_suspicious_payment_patterns(failure_threshold=5)
        assert created == 0


@pytest.mark.django_db
class TestMultiAccountNationalIdDetection:
    def test_flags_shared_national_id(self):
        User.objects.create_user(
            username='acct1', email='acct1@test.com', password='x', role='tenant',
            phone_number='+254700111001', national_id='12345678',
        )
        User.objects.create_user(
            username='acct2', email='acct2@test.com', password='x', role='tenant',
            phone_number='+254700111002', national_id='12345678',
        )
        created = fraud_services.detect_multi_account_national_id()
        assert created == 1
        flag = FraudFlag.objects.get(flag_type=FraudFlag.FlagType.MULTI_ACCOUNT_PHONE)
        assert flag.evidence['account_count'] == 2

    def test_does_not_flag_unique_national_ids(self):
        User.objects.create_user(
            username='acct3', email='acct3@test.com', password='x', role='tenant',
            phone_number='+254700111003', national_id='11111111',
        )
        User.objects.create_user(
            username='acct4', email='acct4@test.com', password='x', role='tenant',
            phone_number='+254700111004', national_id='22222222',
        )
        created = fraud_services.detect_multi_account_national_id()
        assert created == 0

    def test_rerunning_does_not_duplicate_open_flags(self):
        User.objects.create_user(
            username='acct5', email='acct5@test.com', password='x', role='tenant',
            phone_number='+254700111005', national_id='33333333',
        )
        User.objects.create_user(
            username='acct6', email='acct6@test.com', password='x', role='tenant',
            phone_number='+254700111006', national_id='33333333',
        )
        first_run = fraud_services.detect_multi_account_national_id()
        second_run = fraud_services.detect_multi_account_national_id()
        assert first_run == 1
        assert second_run == 0
