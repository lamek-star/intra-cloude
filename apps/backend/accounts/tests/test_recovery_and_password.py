"""MFA recovery codes, changing one's own password, and an administrator's password reset for a staff
member."""

from django.core.cache import cache
from django.test import Client
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from accounts import totp
from accounts.models import User
from organizations.models import Membership
from organizations.services import create_organization
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand
from permissions.services import assign_role

PASSWORD = "a-strong-passw0rd!"


class RecoveryCodeTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="codes@example.com", password=PASSWORD)
        self.client.force_login(self.user)
        self.secret = self.client.post(reverse("mfa-enroll")).data["secret"]
        confirm = self.client.post(reverse("mfa-confirm"), {"code": totp.generate_totp(self.secret)})
        self.codes = confirm.data["recovery_codes"]

    def sign_in_with(self, code):
        client = APIClient()
        self.assertTrue(
            client.post(reverse("auth-login"), {"email": self.user.email, "password": PASSWORD}).data[
                "mfa_required"
            ]
        )
        return client, client.post(reverse("mfa-verify"), {"code": code})

    def test_ten_codes_are_shown_once_and_each_signs_in_one_time(self):
        self.assertEqual(len(self.codes), 10)
        self.assertEqual(len(set(self.codes)), 10)
        self.assertEqual(self.client.get(reverse("mfa-recovery-codes")).data, {"left": 10, "enabled": True})
        client, first = self.sign_in_with(self.codes[0].lower().replace("-", " "))
        self.assertEqual(first.status_code, status.HTTP_200_OK, first.data)
        self.assertEqual(client.get(reverse("auth-me")).status_code, 200)
        cache.clear()
        _, again = self.sign_in_with(self.codes[0])
        self.assertNotEqual(again.status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(reverse("mfa-recovery-codes")).data["left"], 9)

    def test_new_codes_need_a_current_code_and_replace_the_old_ones(self):
        self.assertEqual(self.client.post(reverse("mfa-recovery-codes"), {"code": "000000"}).status_code, 400)
        fresh = self.client.post(
            reverse("mfa-recovery-codes"), {"code": totp.generate_totp(self.secret)}
        ).data
        self.assertEqual(len(fresh["recovery_codes"]), 10)
        cache.clear()
        _, old = self.sign_in_with(self.codes[1])
        self.assertNotEqual(old.status_code, status.HTTP_200_OK)
        cache.clear()
        _, new = self.sign_in_with(fresh["recovery_codes"][0])
        self.assertEqual(new.status_code, status.HTTP_200_OK)

    def test_switching_two_step_off_removes_the_codes(self):
        self.client.post(reverse("mfa-disable"), {"code": totp.generate_totp(self.secret)})
        self.assertEqual(self.client.get(reverse("mfa-recovery-codes")).data, {"left": 0, "enabled": False})


class PasswordChangeTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="changer@example.com", password=PASSWORD)
        self.client.force_login(self.user)

    def test_the_current_password_is_needed_and_the_session_stays_signed_in(self):
        url = reverse("auth-password")
        wrong = self.client.post(url, {"current_password": "nope", "new_password": "Another-passw0rd!"})
        self.assertEqual(wrong.status_code, 400)
        weak = self.client.post(url, {"current_password": PASSWORD, "new_password": "123"})
        self.assertEqual(weak.status_code, 400)
        ok = self.client.post(url, {"current_password": PASSWORD, "new_password": "Another-passw0rd!"})
        self.assertEqual(ok.status_code, 200, ok.data)
        self.assertEqual(self.client.get(reverse("auth-me")).status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Another-passw0rd!"))


class PasswordResetTests(APITestCase):
    def setUp(self):
        cache.clear()
        SeedPermissionsCommand().handle()
        self.owner = User.objects.create_user(email="shop-owner@example.com", password=PASSWORD)
        self.org = create_organization(name="Shop A", created_by=self.owner)
        self.staff = User.objects.create_user(email="staff@example.com", password=PASSWORD)
        self.membership = Membership.objects.create(
            user=self.staff, organization=self.org, status=Membership.Status.ACTIVE
        )
        self.client.force_login(self.owner)

    def url(self, membership=None):
        return reverse("membership-password-reset", args=[self.org.id, (membership or self.membership).id])

    def test_the_owner_resets_a_staff_password_who_is_signed_out_and_must_choose_a_new_one(self):
        staff_browser = Client()
        staff_browser.force_login(self.staff)
        r = self.client.post(self.url())
        self.assertEqual(r.status_code, 200, r.data)
        temporary = r.data["temporary_password"]
        self.assertEqual(staff_browser.get(reverse("auth-me")).status_code, 403)  # signed out everywhere
        fresh = APIClient()
        signed = fresh.post(reverse("auth-login"), {"email": self.staff.email, "password": temporary})
        self.assertEqual(signed.status_code, 200, signed.data)
        self.assertTrue(fresh.get(reverse("auth-me")).data["must_change_password"])
        blocked = fresh.get(reverse("organization-list-create"))
        self.assertEqual((blocked.status_code, blocked.json()["code"]), (403, "password_change_required"))
        changed = fresh.post(
            reverse("auth-password"), {"current_password": temporary, "new_password": "Staff-own-passw0rd!"}
        )
        self.assertEqual(changed.status_code, 200, changed.data)
        self.assertEqual(fresh.get(reverse("organization-list-create")).status_code, 200)

    def test_not_someone_who_also_works_in_an_organization_the_admin_does_not_manage(self):
        other_owner = User.objects.create_user(email="other-owner@example.com", password=PASSWORD)
        other = create_organization(name="Shop B", created_by=other_owner)
        Membership.objects.create(user=self.staff, organization=other, status=Membership.Status.ACTIVE)
        self.assertEqual(self.client.post(self.url()).status_code, 403)
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.check_password(PASSWORD))

    def test_not_the_super_administrator_not_oneself_and_not_by_a_plain_member(self):
        assign_role(user=self.staff, role_slug="super-administrator", organization=None)
        self.assertEqual(self.client.post(self.url()).status_code, 403)
        own = Membership.objects.get(user=self.owner, organization=self.org)
        self.assertEqual(self.client.post(self.url(own)).status_code, 403)
        plain = User.objects.create_user(email="plain@example.com", password=PASSWORD)
        Membership.objects.create(user=plain, organization=self.org, status=Membership.Status.ACTIVE)
        self.client.force_login(plain)
        self.assertEqual(self.client.post(self.url()).status_code, 403)
