from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from applications.models import Application, ApplicationCredential
from organizations.models import Membership
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand


class ApplicationTestBase(APITestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        SeedPermissionsCommand().handle()
        self.admin = User.objects.create_user(email="apps-admin@example.com", password="x")
        self.client.force_login(self.admin)

        org = self.client.post(reverse("organization-list-create"), {"name": "Acme"})
        self.org_id = org.data["id"]
        ws = self.client.post(reverse("workspace-list-create", args=[self.org_id]), {"name": "WS"})
        proj = self.client.post(reverse("project-list-create", args=[ws.data["id"]]), {"name": "Proj"})
        self.project_id = proj.data["id"]

        bucket_a = self.client.post(
            reverse("bucket-list-create", args=[self.project_id]), {"name": "bucket-a"}
        )
        self.bucket_a_id = bucket_a.data["id"]
        bucket_b = self.client.post(
            reverse("bucket-list-create", args=[self.project_id]), {"name": "bucket-b"}
        )
        self.bucket_b_id = bucket_b.data["id"]
        self.client.post(
            reverse("file-list-create", args=[self.bucket_a_id]),
            {"file": SimpleUploadedFile("secret.txt", b"in bucket a", content_type="text/plain")},
            format="multipart",
        )
        self.client.post(
            reverse("file-list-create", args=[self.bucket_b_id]),
            {"file": SimpleUploadedFile("other.txt", b"in bucket b", content_type="text/plain")},
            format="multipart",
        )


class RegistrationTests(ApplicationTestBase):
    def test_register_creates_application_service_account_and_membership(self):
        resp = self.client.post(
            reverse("application-list-create", args=[self.org_id]),
            {"name": "Reporting Bot", "description": "pulls nightly reports"},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        app = Application.objects.get(id=resp.data["id"])
        self.assertTrue(hasattr(app, "service_account"))
        identity_user = app.service_account.identity_user
        self.assertFalse(identity_user.has_usable_password())
        self.assertTrue(
            Membership.objects.filter(
                user=identity_user, organization_id=self.org_id, status=Membership.Status.ACTIVE
            ).exists()
        )

    def test_member_without_application_create_permission_is_forbidden(self):
        member = User.objects.create_user(email="apps-plain@example.com", password="x")
        Membership.objects.create(user=member, organization_id=self.org_id, status=Membership.Status.ACTIVE)
        self.client.force_login(member)

        resp = self.client.post(reverse("application-list-create", args=[self.org_id]), {"name": "X"})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class CredentialLifecycleTests(ApplicationTestBase):
    def setUp(self):
        super().setUp()
        app = self.client.post(reverse("application-list-create", args=[self.org_id]), {"name": "Bot"})
        self.application_id = app.data["id"]

    def _auth_headers(self, token):
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_issue_credential_returns_secret_once_and_never_again(self):
        resp = self.client.post(reverse("application-credential-list-create", args=[self.application_id]))
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("secret", resp.data)
        credential_id = resp.data["id"]

        listing = self.client.get(reverse("application-credential-list-create", args=[self.application_id]))
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertNotIn("secret", listing.data[0])
        self.assertEqual(listing.data[0]["id"], credential_id)

        # The hash is never exposed, and the plaintext is never persisted
        # anywhere the server could hand back out.
        stored = ApplicationCredential.objects.get(id=credential_id)
        self.assertNotEqual(stored.secret_hash, resp.data["secret"])

    def test_valid_credential_authenticates_as_the_service_account(self):
        issued = self.client.post(reverse("application-credential-list-create", args=[self.application_id]))
        token = issued.data["secret"]

        self.client.logout()
        resp = self.client.get(reverse("auth-me"), **self._auth_headers(token))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["email"].startswith("service-account+"))

    def test_service_account_with_no_grants_cannot_read_any_bucket(self):
        """This is the Phase 7 exit criteria: a broad scope with no
        ResourceGrant yields no access at all — not even read access to
        the org's own buckets, despite the service account technically
        being a member of the org (Membership alone grants nothing)."""
        issued = self.client.post(reverse("application-credential-list-create", args=[self.application_id]))
        token = issued.data["secret"]
        self.client.logout()

        resp = self.client.get(
            reverse("file-list-create", args=[self.bucket_a_id]), **self._auth_headers(token)
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_resource_grant_restricts_access_to_exactly_that_bucket(self):
        issued = self.client.post(reverse("application-credential-list-create", args=[self.application_id]))
        token = issued.data["secret"]

        grant = self.client.post(
            reverse("application-resource-grant-list-create", args=[self.application_id]),
            {
                "permission_code": "storage.read",
                "resource_type": "storage.bucket",
                "resource_id": self.bucket_a_id,
            },
            format="json",
        )
        self.assertEqual(grant.status_code, status.HTTP_201_CREATED)

        self.client.logout()

        allowed = self.client.get(
            reverse("file-list-create", args=[self.bucket_a_id]), **self._auth_headers(token)
        )
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)
        self.assertEqual(len(allowed.data), 1)

        denied = self.client.get(
            reverse("file-list-create", args=[self.bucket_b_id]), **self._auth_headers(token)
        )
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

    def test_resource_grant_serializes_granted_by_as_uuid_not_user_str(self):
        """Regression: ResourceGrantSerializer.granted_by was declared a
        UUIDField but read the related User object (via the FK descriptor)
        rather than its id, so DRF's UUIDField.to_representation fell back
        to `str(value)` -- the User model's __str__, i.e. its email -- not
        a UUID. Found live via the frontend applications page (a real
        grant's response had `"granted_by": "apps-admin@example.com"`),
        not by static inspection."""
        grant = self.client.post(
            reverse("application-resource-grant-list-create", args=[self.application_id]),
            {
                "permission_code": "storage.read",
                "resource_type": "storage.bucket",
                "resource_id": self.bucket_a_id,
            },
            format="json",
        )
        self.assertEqual(grant.status_code, status.HTTP_201_CREATED)
        self.assertEqual(grant.data["granted_by"], str(self.admin.id))

        listed = self.client.get(
            reverse("application-resource-grant-list-create", args=[self.application_id])
        )
        self.assertEqual(listed.data[0]["granted_by"], str(self.admin.id))

    def test_revoked_credential_no_longer_authenticates(self):
        issued = self.client.post(reverse("application-credential-list-create", args=[self.application_id]))
        token = issued.data["secret"]
        credential_id = issued.data["id"]

        self.client.post(
            reverse("application-credential-revoke", args=[self.application_id, credential_id])
        )
        self.client.logout()

        resp = self.client.get(reverse("auth-me"), **self._auth_headers(token))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_rotate_invalidates_old_token_and_issues_a_working_new_one(self):
        issued = self.client.post(reverse("application-credential-list-create", args=[self.application_id]))
        old_token = issued.data["secret"]
        credential_id = issued.data["id"]

        rotated = self.client.post(
            reverse("application-credential-rotate", args=[self.application_id, credential_id])
        )
        self.assertEqual(rotated.status_code, status.HTTP_201_CREATED)
        new_token = rotated.data["secret"]
        self.assertNotEqual(old_token, new_token)

        self.client.logout()

        old_resp = self.client.get(reverse("auth-me"), **self._auth_headers(old_token))
        self.assertEqual(old_resp.status_code, status.HTTP_403_FORBIDDEN)

        new_resp = self.client.get(reverse("auth-me"), **self._auth_headers(new_token))
        self.assertEqual(new_resp.status_code, status.HTTP_200_OK)

    def test_garbage_bearer_token_is_rejected_not_crashed_on(self):
        self.client.logout()
        resp = self.client.get(reverse("auth-me"), HTTP_AUTHORIZATION="Bearer not-a-real-token")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_without_credentials_manage_permission_cannot_issue(self):
        member = User.objects.create_user(email="apps-plain2@example.com", password="x")
        Membership.objects.create(user=member, organization_id=self.org_id, status=Membership.Status.ACTIVE)
        self.client.force_login(member)

        resp = self.client.post(reverse("application-credential-list-create", args=[self.application_id]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
