"""
End-to-end coverage of the Authorization Code + PKCE (+ OIDC) flow,
driven through the real HTTP endpoints (never by calling services.py
directly) so this proves the views wire everything up correctly, not
just that the underlying functions are individually correct.
"""

from urllib.parse import parse_qs, urlsplit

import jwt
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from oauth_provider import services
from oauth_provider.models import OAuthAccessToken, OAuthAuthorizationCode
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand

VERIFIER = "a-fixed-high-entropy-code-verifier-1234567890"
REDIRECT_URI = "http://localhost:3000/auth/callback"


def make_client(**overrides):
    defaults = dict(
        name="Test Client", redirect_uris=[REDIRECT_URI],
        post_logout_redirect_uris=[], allowed_origins=[],
    )
    defaults.update(overrides)
    client, secret = services.create_client(**defaults)
    return client, secret


class AuthorizationCodeFlowTests(APITestCase):
    def setUp(self):
        # /oauth/token carries the same tight "auth" throttle scope as
        # login/register (Section 10) -- shared per-IP cache, so tests
        # that call it several times must start from a clean counter
        # exactly like accounts/tests/test_auth.py's own RegisterTests.
        cache.clear()
        SeedPermissionsCommand().handle()  # organizations.services.create_organization needs Role rows to exist.
        self.user = User.objects.create_user(email="rider@example.com", password="x", first_name="Rider")
        self.client_app, self.client_secret = make_client()

    def _authorize(self, **params):
        query = {
            "response_type": "code",
            "client_id": self.client_app.client_id,
            "redirect_uri": REDIRECT_URI,
            "scope": "openid profile email",
            "state": "xyz",
            "code_challenge": services.compute_s256_challenge(VERIFIER),
            "code_challenge_method": "S256",
            "nonce": "nonce-abc",
        }
        query.update(params)
        return self.client.get(reverse("oauth-authorize"), query)

    def test_unauthenticated_user_is_sent_to_login_with_return_path(self):
        response = self._authorize()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/login?next="))
        self.assertIn("oauth%2Fauthorize", response.url)

    def test_valid_request_from_an_authenticated_user_issues_a_code_and_redirects(self):
        self.client.force_login(self.user)
        response = self._authorize()
        self.assertEqual(response.status_code, 302)
        parsed = urlsplit(response.url)
        self.assertEqual(f"{parsed.scheme}://{parsed.netloc}{parsed.path}", REDIRECT_URI)
        params = parse_qs(parsed.query)
        self.assertEqual(params["state"], ["xyz"])
        self.assertIn("code", params)
        self.assertTrue(
            OAuthAuthorizationCode.objects.filter(client=self.client_app, user=self.user).exists()
        )

    def test_unknown_client_id_does_not_redirect_anywhere(self):
        self.client.force_login(self.user)
        response = self._authorize(client_id="not-a-real-client")
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("Location", response.headers)

    def test_disabled_client_is_refused_exactly_like_an_unknown_one(self):
        self.client_app.enabled = False
        self.client_app.save(update_fields=["enabled"])
        self.client.force_login(self.user)
        response = self._authorize()
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("Location", response.headers)

    def test_unregistered_redirect_uri_is_never_redirected_to_an_open_redirect(self):
        self.client.force_login(self.user)
        response = self._authorize(redirect_uri="https://evil.example.com/steal")
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("Location", response.headers)
        self.assertNotIn("evil.example.com", response.content.decode())

    def test_missing_pkce_challenge_is_reported_via_redirect_not_a_code(self):
        self.client.force_login(self.user)
        response = self._authorize(code_challenge="", code_challenge_method="")
        self.assertEqual(response.status_code, 302)
        params = parse_qs(urlsplit(response.url).query)
        self.assertEqual(params["error"], ["invalid_request"])
        self.assertFalse(OAuthAuthorizationCode.objects.exists())

    def _exchange(self, **overrides):
        body = {
            "grant_type": "authorization_code",
            "client_id": self.client_app.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": REDIRECT_URI,
            "code_verifier": VERIFIER,
        }
        body.update(overrides)
        return self.client.post(reverse("oauth-token"), body)

    def _get_code(self, **authorize_overrides):
        self.client.force_login(self.user)
        response = self._authorize(**authorize_overrides)
        code = parse_qs(urlsplit(response.url).query)["code"][0]
        self.client.logout()
        return code

    def test_full_round_trip_returns_access_token_and_a_verifiable_id_token(self):
        code = self._get_code()
        response = self._exchange(code=code)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["token_type"], "Bearer")
        self.assertIn("access_token", response.data)
        self.assertIn("id_token", response.data)

        jwks = services.jwks()
        signing_key = jwks["keys"][0]
        # Full, real signature verification against the published JWKS --
        # not just "a token-shaped string came back".
        public_numbers_key = jwt.algorithms.RSAAlgorithm.from_jwk(__import__("json").dumps(signing_key))
        claims = jwt.decode(
            response.data["id_token"], key=public_numbers_key, algorithms=["RS256"],
            audience=self.client_app.client_id, issuer="https://localhost:8443",
        )
        self.assertEqual(claims["sub"], str(self.user.id))
        self.assertEqual(claims["email"], "rider@example.com")
        self.assertEqual(claims["name"], "Rider")
        self.assertEqual(claims["nonce"], "nonce-abc")
        self.assertEqual(claims["aud"], self.client_app.client_id)

    def test_authorization_code_is_single_use(self):
        code = self._get_code()
        first = self._exchange(code=code)
        self.assertEqual(first.status_code, 200)
        second = self._exchange(code=code)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(second.data["error"], "invalid_grant")

    def test_expired_authorization_code_is_refused(self):
        code = self._get_code()
        OAuthAuthorizationCode.objects.update(expires_at=timezone.now() - timezone.timedelta(seconds=1))
        response = self._exchange(code=code)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "invalid_grant")

    def test_code_cannot_be_redeemed_by_a_different_client(self):
        other_client, other_secret = make_client(name="Other Client")
        code = self._get_code()
        response = self._exchange(code=code, client_id=other_client.client_id, client_secret=other_secret)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "invalid_grant")

    def test_redirect_uri_must_match_exactly_at_token_exchange(self):
        code = self._get_code()
        response = self._exchange(code=code, redirect_uri=REDIRECT_URI + "/extra")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "invalid_grant")

    def test_wrong_pkce_verifier_is_refused(self):
        code = self._get_code()
        response = self._exchange(code=code, code_verifier="not-the-right-verifier")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "invalid_grant")

    def test_invalid_client_secret_is_refused(self):
        code = self._get_code()
        response = self._exchange(code=code, client_secret="wrong-secret")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "invalid_client")

    def test_disabled_client_cannot_redeem_a_code_it_issued_before_being_disabled(self):
        code = self._get_code()
        self.client_app.enabled = False
        self.client_app.save(update_fields=["enabled"])
        response = self._exchange(code=code)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "invalid_client")

    def test_userinfo_with_a_valid_access_token(self):
        code = self._get_code()
        token_response = self._exchange(code=code)
        response = self.client.get(
            reverse("oauth-userinfo"), HTTP_AUTHORIZATION=f"Bearer {token_response.data['access_token']}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["sub"], str(self.user.id))
        self.assertEqual(response.data["email"], "rider@example.com")

    def test_userinfo_rejects_an_expired_access_token(self):
        code = self._get_code()
        token_response = self._exchange(code=code)
        OAuthAccessToken.objects.update(expires_at=timezone.now() - timezone.timedelta(seconds=1))
        response = self.client.get(
            reverse("oauth-userinfo"), HTTP_AUTHORIZATION=f"Bearer {token_response.data['access_token']}"
        )
        self.assertEqual(response.status_code, 401)

    def test_userinfo_rejects_a_garbage_token(self):
        response = self.client.get(reverse("oauth-userinfo"), HTTP_AUTHORIZATION="Bearer not-a-real-token")
        self.assertEqual(response.status_code, 401)

    def test_revoke_then_userinfo_fails(self):
        code = self._get_code()
        token_response = self._exchange(code=code)
        revoke = self.client.post(reverse("oauth-revoke"), {"token": token_response.data["access_token"]})
        self.assertEqual(revoke.status_code, 200)
        userinfo = self.client.get(
            reverse("oauth-userinfo"), HTTP_AUTHORIZATION=f"Bearer {token_response.data['access_token']}"
        )
        self.assertEqual(userinfo.status_code, 401)

    def test_revoking_an_unknown_token_is_still_200(self):
        response = self.client.post(reverse("oauth-revoke"), {"token": "never-issued"})
        self.assertEqual(response.status_code, 200)

    def test_org_less_user_gets_a_stable_sub_and_no_organization_claim(self):
        code = self._get_code()
        response = self._exchange(code=code)
        jwks = services.jwks()
        import json as _json

        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(_json.dumps(jwks["keys"][0]))
        claims = jwt.decode(
            response.data["id_token"], key=public_key, algorithms=["RS256"],
            audience=self.client_app.client_id, issuer="https://localhost:8443",
        )
        self.assertEqual(claims["sub"], str(self.user.id))
        self.assertNotIn("org", claims)
        self.assertNotIn("organization", claims)
        self.assertNotIn("org_id", claims)

    def test_sub_is_unchanged_after_the_user_later_creates_an_organization(self):
        from organizations.services import create_organization

        code = self._get_code()
        sub_before = self._exchange(code=code).data
        create_organization(name="Later Org", created_by=self.user)

        second_code = self._get_code()
        sub_after = self._exchange(code=second_code).data
        self.assertEqual(
            jwt.decode(sub_before["id_token"], options={"verify_signature": False})["sub"],
            jwt.decode(sub_after["id_token"], options={"verify_signature": False})["sub"],
        )

    def test_scope_without_email_omits_the_email_claim(self):
        self.client.force_login(self.user)
        response = self._authorize(scope="openid")
        code = parse_qs(urlsplit(response.url).query)["code"][0]
        self.client.logout()
        token_response = self._exchange(code=code)
        claims = jwt.decode(token_response.data["id_token"], options={"verify_signature": False})
        self.assertNotIn("email", claims)
        self.assertEqual(claims["sub"], str(self.user.id))
