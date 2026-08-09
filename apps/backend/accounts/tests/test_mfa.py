"""
Phase 10: TOTP-based MFA (enrollment, login enforcement) and the
gateway-mode requirement that new administrative role grants need MFA
already enabled on the target user.
"""

from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts import totp
from accounts.models import User
from organizations.models import Membership, Organization
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand
from permissions.services import PermissionError_, assign_role


class MFATestBase(APITestCase):
    def setUp(self):
        # The login/register/mfa-verify endpoints carry a tight "auth"
        # throttle scope (Phase 10) keyed by client IP in the shared
        # test-process cache — clear it per test class so results never
        # depend on what ran earlier in the suite.
        cache.clear()
        self.user = User.objects.create_user(email="mfa-user@example.com", password="a-strong-passw0rd!")
        self.client.force_login(self.user)


class EnrollmentTests(MFATestBase):
    def test_enroll_then_confirm_with_a_real_generated_code_enables_mfa(self):
        enroll = self.client.post(reverse("mfa-enroll"))
        self.assertEqual(enroll.status_code, status.HTTP_201_CREATED)
        secret = enroll.data["secret"]
        self.assertIn("otpauth://totp/", enroll.data["provisioning_uri"])

        code = totp.generate_totp(secret)
        confirm = self.client.post(reverse("mfa-confirm"), {"code": code})
        self.assertEqual(confirm.status_code, status.HTTP_200_OK)
        self.assertTrue(confirm.data["mfa_enabled"])

        self.user.refresh_from_db()
        self.assertTrue(self.user.mfa_enabled)
        self.assertIsNotNone(self.user.mfa_confirmed_at)

    def test_confirm_with_wrong_code_does_not_enable_mfa(self):
        self.client.post(reverse("mfa-enroll"))
        resp = self.client.post(reverse("mfa-confirm"), {"code": "000000"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

        self.user.refresh_from_db()
        self.assertFalse(self.user.mfa_enabled)

    def test_confirm_without_a_prior_enroll_call_is_rejected(self):
        resp = self.client.post(reverse("mfa-confirm"), {"code": "123456"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_disable_requires_a_valid_current_code(self):
        enroll = self.client.post(reverse("mfa-enroll"))
        secret = enroll.data["secret"]
        self.client.post(reverse("mfa-confirm"), {"code": totp.generate_totp(secret)})

        bad = self.client.post(reverse("mfa-disable"), {"code": "000000"})
        self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.mfa_enabled)

        good = self.client.post(reverse("mfa-disable"), {"code": totp.generate_totp(secret)})
        self.assertEqual(good.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertFalse(self.user.mfa_enabled)
        self.assertIsNone(self.user.mfa_secret_encrypted)


class LoginWithMFATests(MFATestBase):
    def setUp(self):
        super().setUp()
        enroll = self.client.post(reverse("mfa-enroll"))
        self.secret = enroll.data["secret"]
        self.client.post(reverse("mfa-confirm"), {"code": totp.generate_totp(self.secret)})
        self.client.logout()

    def test_password_alone_does_not_complete_login(self):
        resp = self.client.post(
            reverse("auth-login"), {"email": "mfa-user@example.com", "password": "a-strong-passw0rd!"}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["mfa_required"])

        # No full session was established — an authenticated-only
        # endpoint is still unreachable.
        me = self.client.get(reverse("auth-me"))
        self.assertEqual(me.status_code, status.HTTP_403_FORBIDDEN)

    def test_correct_code_after_password_completes_login(self):
        self.client.post(
            reverse("auth-login"), {"email": "mfa-user@example.com", "password": "a-strong-passw0rd!"}
        )
        verify = self.client.post(reverse("mfa-verify"), {"code": totp.generate_totp(self.secret)})
        self.assertEqual(verify.status_code, status.HTTP_200_OK)
        self.assertEqual(verify.data["email"], "mfa-user@example.com")

        me = self.client.get(reverse("auth-me"))
        self.assertEqual(me.status_code, status.HTTP_200_OK)

    def test_wrong_code_after_password_does_not_complete_login(self):
        self.client.post(
            reverse("auth-login"), {"email": "mfa-user@example.com", "password": "a-strong-passw0rd!"}
        )
        verify = self.client.post(reverse("mfa-verify"), {"code": "000000"})
        self.assertEqual(verify.status_code, status.HTTP_401_UNAUTHORIZED)

        me = self.client.get(reverse("auth-me"))
        self.assertEqual(me.status_code, status.HTTP_403_FORBIDDEN)

    def test_verify_without_a_pending_login_is_rejected(self):
        resp = self.client.post(reverse("mfa-verify"), {"code": totp.generate_totp(self.secret)})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class AuthThrottleTests(MFATestBase):
    def test_login_endpoint_is_throttled_after_repeated_attempts(self):
        self.client.logout()
        last_status = None
        for _ in range(11):
            resp = self.client.post(
                reverse("auth-login"), {"email": "mfa-user@example.com", "password": "wrong"}
            )
            last_status = resp.status_code
        self.assertEqual(last_status, status.HTTP_429_TOO_MANY_REQUESTS)


class AdminRoleMFAEnforcementTests(APITestCase):
    def setUp(self):
        cache.clear()
        SeedPermissionsCommand().handle()
        self.admin = User.objects.create_user(email="gw-admin@example.com", password="x")
        self.client.force_login(self.admin)
        org = self.client.post(reverse("organization-list-create"), {"name": "Acme"})
        self.org_id = org.data["id"]

        self.org = Organization.objects.get(id=self.org_id)
        self.target = User.objects.create_user(email="gw-target@example.com", password="x")
        self.membership = Membership.objects.create(
            user=self.target, organization=self.org, status=Membership.Status.ACTIVE
        )

    @override_settings(FEATURE_INTERNET_GATEWAY_ENABLED=True)
    def test_assigning_an_admin_role_to_a_user_without_mfa_is_rejected_in_gateway_mode(self):
        with self.assertRaises(PermissionError_):
            assign_role(
                user=self.target,
                role_slug="organization-administrator",
                organization=self.org,
                granted_by=self.admin,
            )

    @override_settings(FEATURE_INTERNET_GATEWAY_ENABLED=True)
    def test_assigning_an_admin_role_succeeds_once_the_target_has_mfa_enabled(self):
        self.target.mfa_enabled = True
        self.target.save(update_fields=["mfa_enabled"])

        assignment = assign_role(
            user=self.target,
            role_slug="organization-administrator",
            organization=self.org,
            granted_by=self.admin,
        )
        self.assertIsNotNone(assignment.id)

    def test_assigning_an_admin_role_is_unrestricted_when_gateway_mode_is_off(self):
        assignment = assign_role(
            user=self.target,
            role_slug="organization-administrator",
            organization=self.org,
            granted_by=self.admin,
        )
        self.assertIsNotNone(assignment.id)

    @override_settings(FEATURE_INTERNET_GATEWAY_ENABLED=True)
    def test_org_creator_self_assignment_is_exempt_even_without_mfa(self):
        # organizations.services.create_organization grants the creator
        # organization-administrator with granted_by=created_by (self-
        # assignment) — this must not deadlock a brand-new org creator
        # who can't possibly have MFA enabled before their first org
        # exists.
        resp = self.client.post(reverse("organization-list-create"), {"name": "Second Org"})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
