from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User


class RegisterTests(APITestCase):
    def test_register_creates_user_and_starts_a_session(self):
        response = self.client.post(
            reverse("auth-register"),
            {"email": "new@example.com", "password": "a-strong-passw0rd!", "first_name": "New"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="new@example.com").exists())

        me = self.client.get(reverse("auth-me"))
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertEqual(me.data["email"], "new@example.com")

    def test_register_rejects_duplicate_email(self):
        User.objects.create_user(email="dupe@example.com", password="a-strong-passw0rd!")
        response = self.client.post(
            reverse("auth-register"), {"email": "dupe@example.com", "password": "a-strong-passw0rd!"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_rejects_weak_password(self):
        response = self.client.post(
            reverse("auth-register"), {"email": "weak@example.com", "password": "1234567890"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginLogoutTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@example.com", password="a-strong-passw0rd!")

    def test_login_with_correct_credentials(self):
        response = self.client.post(
            reverse("auth-login"), {"email": "user@example.com", "password": "a-strong-passw0rd!"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "user@example.com")

    def test_login_with_wrong_password_is_rejected(self):
        response = self.client.post(
            reverse("auth-login"), {"email": "user@example.com", "password": "wrong"}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_with_unknown_email_is_rejected(self):
        response = self.client.post(
            reverse("auth-login"), {"email": "nobody@example.com", "password": "whatever"}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_inactive_user_cannot_log_in(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        response = self.client.post(
            reverse("auth-login"), {"email": "user@example.com", "password": "a-strong-passw0rd!"}
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_requires_authentication(self):
        response = self.client.get(reverse("auth-me"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_logout_ends_the_session(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("auth-logout"))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        me = self.client.get(reverse("auth-me"))
        self.assertEqual(me.status_code, status.HTTP_403_FORBIDDEN)
