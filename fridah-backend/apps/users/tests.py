from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from apps.factories import UserFactory
from apps.users.models import User, OTP


class RegistrationTests(APITestCase):
    def test_register_creates_user_and_returns_tokens(self):
        payload = {
            "username": "janedoe",
            "email": "jane@example.com",
            "phone_number": "+254712345678",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
            "first_name": "Jane",
            "last_name": "Doe",
            "role": "tenant",
            "county": "Nairobi",
            "town": "Kasarani",
        }
        response = self.client.post(reverse('register'), payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertIn('tokens', response.data['data'])
        self.assertTrue(User.objects.filter(email="jane@example.com").exists())
        self.assertTrue(OTP.objects.filter(purpose=OTP.Purpose.REGISTRATION).exists())

    def test_register_password_mismatch_fails(self):
        payload = {
            "username": "janedoe2", "email": "jane2@example.com", "phone_number": "+254712345679",
            "password": "StrongPass123!", "password_confirm": "Different123!",
            "role": "tenant",
        }
        response = self.client.post(reverse('register'), payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginTests(APITestCase):
    def setUp(self):
        self.user = UserFactory(email="login@example.com", password="MyPass123!")

    def test_login_success(self):
        response = self.client.post(reverse('login'), {"email": "login@example.com", "password": "MyPass123!"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', response.data['data'])

    def test_login_invalid_credentials(self):
        response = self.client.post(reverse('login'), {"email": "login@example.com", "password": "wrong"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class KYCTests(APITestCase):
    def setUp(self):
        self.user = UserFactory(password="MyPass123!")
        self.client.force_authenticate(self.user)

    def test_kyc_pending_list_requires_admin(self):
        response = self.client.get(reverse('kyc_pending'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
