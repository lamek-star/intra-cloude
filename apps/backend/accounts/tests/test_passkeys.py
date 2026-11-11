"""
Passkeys (ADR-0019), end to end through the HTTP API. `SoftAuthenticator` is a minimal software FIDO2
authenticator -- a real P-256 key, real CBOR attestation (fmt "none") and real ECDSA assertion signatures --
so the `webauthn` library's verification runs exactly as it does for a phone; nothing is mocked.
"""

import hashlib
import json
import os
import struct

import cbor2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from django.core.cache import cache
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url

from accounts import totp
from accounts.models import Passkey, User
from audit.models import AuditEvent

PASSWORD = "a-strong-passw0rd!"
ORIGIN = "http://testserver"
RP_ID = "testserver"


class SoftAuthenticator:
    def __init__(self, user_handle: bytes | None = None, origin: str = ORIGIN, rp_id: str = RP_ID):
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.credential_id = os.urandom(32)
        self.user_handle = user_handle
        self.origin = origin
        self.rp_id = rp_id
        self.counter = 0

    def _cose_key(self) -> bytes:
        numbers = self.key.public_key().public_numbers()
        return cbor2.dumps(
            {1: 2, 3: -7, -1: 1, -2: numbers.x.to_bytes(32, "big"), -3: numbers.y.to_bytes(32, "big")}
        )

    def _client_data(self, kind: str, challenge: str) -> bytes:
        return json.dumps(
            {"type": kind, "challenge": challenge, "origin": self.origin, "crossOrigin": False}
        ).encode()

    def create(self, options: dict) -> dict:
        self.user_handle = base64url_to_bytes(options["user"]["id"])
        client_data = self._client_data("webauthn.create", options["challenge"])
        flags = (
            0x01 | 0x04 | 0x08 | 0x10 | 0x40
        )  # user present, user verified, backup eligible, backed up, attested data
        auth_data = (
            hashlib.sha256(self.rp_id.encode()).digest()
            + bytes([flags])
            + struct.pack(">I", self.counter)
            + bytes(16)
            + struct.pack(">H", len(self.credential_id))
            + self.credential_id
            + self._cose_key()
        )
        attestation = cbor2.dumps({"fmt": "none", "attStmt": {}, "authData": auth_data})
        cid = bytes_to_base64url(self.credential_id)
        return {
            "id": cid,
            "rawId": cid,
            "type": "public-key",
            "response": {
                "clientDataJSON": bytes_to_base64url(client_data),
                "attestationObject": bytes_to_base64url(attestation),
                "transports": ["hybrid", "internal"],
            },
        }

    def get(self, options: dict, *, user_verified: bool = True, counter: int | None = None) -> dict:
        self.counter = self.counter + 1 if counter is None else counter
        client_data = self._client_data("webauthn.get", options["challenge"])
        flags = 0x01 | (0x04 if user_verified else 0) | 0x08 | 0x10
        auth_data = (
            hashlib.sha256(self.rp_id.encode()).digest() + bytes([flags]) + struct.pack(">I", self.counter)
        )
        signature = self.key.sign(auth_data + hashlib.sha256(client_data).digest(), ec.ECDSA(hashes.SHA256()))
        cid = bytes_to_base64url(self.credential_id)
        return {
            "id": cid,
            "rawId": cid,
            "type": "public-key",
            "response": {
                "clientDataJSON": bytes_to_base64url(client_data),
                "authenticatorData": bytes_to_base64url(auth_data),
                "signature": bytes_to_base64url(signature),
                "userHandle": bytes_to_base64url(self.user_handle or b""),
            },
        }


class PasskeyTestBase(APITestCase):
    def setUp(self):
        cache.clear()  # the "auth" throttle scope is 10/minute per client
        self.user = User.objects.create_user(email="owner@example.com", password=PASSWORD)
        self.client.force_login(self.user)

    def add_passkey(self, *, name="My phone", user=None) -> SoftAuthenticator:
        options = self.client.post(reverse("passkey-register-options"), {"password": PASSWORD}, format="json")
        self.assertEqual(options.status_code, status.HTTP_200_OK, options.data)
        phone = SoftAuthenticator()
        done = self.client.post(
            reverse("passkey-register-verify"),
            {"credential": phone.create(options.data), "name": name},
            format="json",
        )
        self.assertEqual(done.status_code, status.HTTP_201_CREATED, done.data)
        return phone

    def passkey_sign_in(self, phone: SoftAuthenticator, **kwargs):
        options = self.client.post(reverse("passkey-check-options"), {}, format="json")
        self.assertEqual(options.status_code, status.HTTP_200_OK, options.data)
        return self.client.post(
            reverse("passkey-check-verify"), {"credential": phone.get(options.data, **kwargs)}, format="json"
        )


class RegistrationTests(PasskeyTestBase):
    def test_adding_a_passkey_needs_the_password_again(self):
        resp = self.client.post(reverse("passkey-register-options"), {"password": "wrong"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Passkey.objects.exists())

    def test_adding_a_passkey_also_needs_the_authenticator_code_when_two_step_is_on(self):
        secret = self.client.post(reverse("mfa-enroll")).data["secret"]
        self.client.post(reverse("mfa-confirm"), {"code": totp.generate_totp(secret)})
        resp = self.client.post(reverse("passkey-register-options"), {"password": PASSWORD}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        resp = self.client.post(
            reverse("passkey-register-options"),
            {"password": PASSWORD, "code": totp.generate_totp(secret)},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_options_ask_for_a_discoverable_biometric_passkey_on_the_phone_first(self):
        data = self.client.post(
            reverse("passkey-register-options"), {"password": PASSWORD}, format="json"
        ).data
        self.assertEqual(data["rp"]["id"], RP_ID)
        self.assertEqual(data["authenticatorSelection"]["residentKey"], "required")
        self.assertEqual(data["authenticatorSelection"]["userVerification"], "required")
        self.assertEqual(data["hints"], ["hybrid"])

    def test_a_passkey_is_stored_with_its_address_and_audited(self):
        self.add_passkey()
        passkey = Passkey.objects.get()
        self.assertEqual((passkey.user, passkey.rp_id, passkey.name), (self.user, RP_ID, "My phone"))
        self.assertEqual(passkey.transports, ["hybrid", "internal"])
        self.assertTrue(passkey.backed_up)
        self.assertTrue(AuditEvent.objects.filter(action="passkey.add", actor=self.user).exists())

    def test_an_answer_from_another_website_is_refused(self):
        options = self.client.post(
            reverse("passkey-register-options"), {"password": PASSWORD}, format="json"
        ).data
        phone = SoftAuthenticator(origin="https://evil.example")
        resp = self.client.post(
            reverse("passkey-register-verify"), {"credential": phone.create(options)}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Passkey.objects.exists())

    def test_an_answer_without_a_started_request_is_refused(self):
        phone = SoftAuthenticator()
        fake = {
            "challenge": bytes_to_base64url(os.urandom(32)),
            "user": {"id": bytes_to_base64url(self.user.id.bytes)},
        }
        resp = self.client.post(
            reverse("passkey-register-verify"), {"credential": phone.create(fake)}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(ALLOWED_HOSTS=["testserver", "127.0.0.1"])
    def test_an_ip_address_cannot_have_passkeys(self):
        resp = self.client.post(
            reverse("passkey-register-options"), {"password": PASSWORD}, format="json", HTTP_HOST="127.0.0.1"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name in the address", resp.data["detail"])


class SignInTests(PasskeyTestBase):
    def test_signing_in_with_the_passkey_and_no_password(self):
        phone = self.add_passkey()
        self.client.logout()
        resp = self.passkey_sign_in(phone)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["email"], self.user.email)
        self.assertEqual(self.client.get(reverse("auth-me")).status_code, status.HTTP_200_OK)
        self.assertTrue(
            AuditEvent.objects.filter(
                action="auth.login", actor=self.user, context__method="passkey"
            ).exists()
        )

    def test_sign_in_options_reveal_no_account(self):
        self.add_passkey()
        self.client.logout()
        data = self.client.post(reverse("passkey-check-options"), {}, format="json").data
        self.assertEqual(data.get("allowCredentials", []), [])
        self.assertEqual(data["userVerification"], "required")

    def test_a_passkey_sign_in_skips_the_authenticator_code(self):
        secret = self.client.post(reverse("mfa-enroll")).data["secret"]
        self.client.post(reverse("mfa-confirm"), {"code": totp.generate_totp(secret)})
        options = self.client.post(
            reverse("passkey-register-options"),
            {"password": PASSWORD, "code": totp.generate_totp(secret)},
            format="json",
        ).data
        phone = SoftAuthenticator()
        self.client.post(
            reverse("passkey-register-verify"), {"credential": phone.create(options)}, format="json"
        )
        self.client.logout()
        self.assertEqual(self.passkey_sign_in(phone).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(reverse("auth-me")).status_code, status.HTTP_200_OK)

    def test_without_the_biometric_or_pin_the_passkey_is_refused(self):
        phone = self.add_passkey()
        self.client.logout()
        self.assertEqual(
            self.passkey_sign_in(phone, user_verified=False).status_code, status.HTTP_401_UNAUTHORIZED
        )
        self.assertEqual(self.client.get(reverse("auth-me")).status_code, status.HTTP_403_FORBIDDEN)

    def test_the_same_answer_cannot_be_used_twice(self):
        phone = self.add_passkey()
        self.client.logout()
        options = self.client.post(reverse("passkey-check-options"), {}, format="json").data
        answer = phone.get(options)
        self.assertEqual(
            self.client.post(
                reverse("passkey-check-verify"), {"credential": answer}, format="json"
            ).status_code,
            status.HTTP_200_OK,
        )
        self.client.logout()
        self.assertEqual(
            self.client.post(
                reverse("passkey-check-verify"), {"credential": answer}, format="json"
            ).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_a_copied_passkey_whose_counter_goes_back_is_refused(self):
        phone = self.add_passkey()
        self.client.logout()
        self.assertEqual(self.passkey_sign_in(phone, counter=5).status_code, status.HTTP_200_OK)
        self.client.logout()
        self.assertEqual(self.passkey_sign_in(phone, counter=3).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_an_unknown_passkey_is_refused(self):
        self.add_passkey()
        self.client.logout()
        options = self.client.post(reverse("passkey-check-options"), {}, format="json").data
        stranger = SoftAuthenticator(user_handle=self.user.id.bytes)
        resp = self.client.post(
            reverse("passkey-check-verify"), {"credential": stranger.get(options)}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_a_locked_account_cannot_sign_in_with_its_passkey(self):
        phone = self.add_passkey()
        self.client.logout()
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.assertEqual(self.passkey_sign_in(phone).status_code, status.HTTP_401_UNAUTHORIZED)


class PasskeyOnlyTests(PasskeyTestBase):
    def test_passkey_only_needs_a_passkey_first(self):
        resp = self.client.post(reverse("passkey-only"), {"on": True, "password": PASSWORD}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_passkey_only_refuses_even_the_right_password(self):
        phone = self.add_passkey()
        resp = self.client.post(reverse("passkey-only"), {"on": True, "password": PASSWORD}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["passkey_only"])
        self.client.logout()
        resp = self.client.post(
            reverse("auth-login"), {"email": self.user.email, "password": PASSWORD}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(resp.data["passkey_only"])
        self.assertEqual(self.client.get(reverse("auth-me")).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.passkey_sign_in(phone).status_code, status.HTTP_200_OK)

    def test_switching_passkey_only_off_needs_a_fresh_passkey_check(self):
        phone = self.add_passkey()
        self.client.post(reverse("passkey-only"), {"on": True, "password": PASSWORD}, format="json")
        resp = self.client.post(reverse("passkey-only"), {"on": False, "password": PASSWORD}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.passkey_sign_in(phone).status_code, status.HTTP_200_OK)  # signed in: a check
        resp = self.client.post(reverse("passkey-only"), {"on": False}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertFalse(resp.data["passkey_only"])
        self.assertTrue(AuditEvent.objects.filter(action="passkey.only_off", actor=self.user).exists())

    def test_the_last_passkey_cannot_be_removed_while_passkey_only(self):
        self.add_passkey()
        self.client.post(reverse("passkey-only"), {"on": True, "password": PASSWORD}, format="json")
        passkey = Passkey.objects.get()
        resp = self.client.post(
            reverse("passkey-remove", args=[passkey.id]), {"password": PASSWORD}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Passkey.objects.filter(pk=passkey.pk).exists())

    def test_the_server_command_lets_the_owner_back_in_after_losing_the_phone(self):
        self.add_passkey()
        self.client.post(reverse("passkey-only"), {"on": True, "password": PASSWORD}, format="json")
        call_command("passkey_reset", self.user.email, "--remove-all", stdout=open(os.devnull, "w"))
        self.user.refresh_from_db()
        self.assertFalse(self.user.passkey_only)
        self.assertFalse(Passkey.objects.exists())
        self.assertTrue(AuditEvent.objects.filter(action="passkey.reset").exists())


class IsolationTests(PasskeyTestBase):
    """One person's passkeys are theirs alone (IDOR by ID substitution)."""

    def setUp(self):
        super().setUp()
        self.phone = self.add_passkey()
        self.other = User.objects.create_user(email="other@example.com", password=PASSWORD)
        self.client.force_login(self.other)

    def test_another_person_sees_none_of_my_passkeys(self):
        resp = self.client.get(reverse("passkey-list"))
        self.assertEqual(resp.data["passkeys"], [])

    def test_another_person_cannot_remove_my_passkey(self):
        passkey = Passkey.objects.get(user=self.user)
        resp = self.client.post(
            reverse("passkey-remove", args=[passkey.id]), {"password": PASSWORD}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Passkey.objects.filter(pk=passkey.pk).exists())

    def test_my_passkey_does_not_count_as_a_check_for_someone_else(self):
        resp = self.client.post(reverse("passkey-check-options"), {}, format="json")
        self.assertEqual(
            resp.status_code, status.HTTP_400_BAD_REQUEST
        )  # the other person has no passkey here
        # Once they have one, a started check still refuses the owner's passkey for this account.
        other_phone = SoftAuthenticator()
        options = self.client.post(
            reverse("passkey-register-options"), {"password": PASSWORD}, format="json"
        ).data
        self.client.post(
            reverse("passkey-register-verify"), {"credential": other_phone.create(options)}, format="json"
        )
        check = self.client.post(reverse("passkey-check-options"), {}, format="json").data
        resp = self.client.post(
            reverse("passkey-check-verify"), {"credential": self.phone.get(check)}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
