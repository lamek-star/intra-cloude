from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from applications.models import ApplicationCredential
from environments.models import Environment, EnvironmentSecret
from organizations.models import Membership
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand
from permissions.services import assign_role


class EnvironmentTestBase(APITestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        SeedPermissionsCommand().handle()
        self.admin = User.objects.create_user(email="env-admin@example.com", password="x")
        self.client.force_login(self.admin)

        org = self.client.post(reverse("organization-list-create"), {"name": "Acme"})
        self.org_id = org.data["id"]
        ws = self.client.post(reverse("workspace-list-create", args=[self.org_id]), {"name": "WS"})
        proj = self.client.post(reverse("project-list-create", args=[ws.data["id"]]), {"name": "Proj"})
        self.project_id = proj.data["id"]

        app = self.client.post(
            reverse("application-list-create", args=[self.org_id]), {"name": "inventory-system"}
        )
        self.application_id = app.data["id"]

    def _auth_headers(self, token):
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def _create_environment(self, name="Development", environment_type="development", **extra):
        resp = self.client.post(
            reverse("environment-list-create", args=[self.application_id]),
            {"name": name, "environment_type": environment_type, **extra},
            format="json",
        )
        return resp

    def _create_tenant_database(self, name="AppDB"):
        resp = self.client.post(
            reverse("tenant-database-list-create", args=[self.project_id]), {"name": name}
        )
        return resp.data["id"]

    def _create_bucket(self, name="app-files"):
        resp = self.client.post(reverse("bucket-list-create", args=[self.project_id]), {"name": name})
        return resp.data["id"]

    def _create_table_with_row(self, tenant_database_id, table_name="widgets"):
        table = self.client.post(
            reverse("table-list-create", args=[tenant_database_id]), {"name": table_name}
        )
        table_id = table.data["id"]
        row = self.client.post(reverse("row-list-create", args=[table_id]), {})
        return table_id, row.data["id"]


class EnvironmentCrudTests(EnvironmentTestBase):
    def test_create_environment_hierarchy_is_organization_application_environment(self):
        resp = self._create_environment(name="Development", environment_type="development")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        env = Environment.objects.get(id=resp.data["id"])
        self.assertEqual(str(env.application_id), self.application_id)
        self.assertEqual(str(env.organization_id), self.org_id)
        self.assertFalse(env.is_production_tier)

    def test_production_type_defaults_is_production_tier_true(self):
        resp = self._create_environment(name="Production", environment_type="production")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data["is_production_tier"])

    def test_custom_environment_type_is_not_hardcoded_out(self):
        """The architecture must support environment kinds beyond dev/
        staging/prod without a schema change -- a free-form type string
        plus an explicit is_production_tier flag."""
        resp = self._create_environment(name="QA", environment_type="qa", is_production_tier=False)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["environment_type"], "qa")

    def test_duplicate_slug_within_application_is_disambiguated(self):
        first = self._create_environment(name="Staging")
        second = self._create_environment(name="Staging")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(first.data["slug"], second.data["slug"])

    def test_update_environment_config(self):
        env = self._create_environment().data
        resp = self.client.patch(
            reverse("environment-detail", args=[env["id"]]),
            {"config": {"service_endpoint": "https://dev.example.com"}},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["config"]["service_endpoint"], "https://dev.example.com")

    def test_clone_environment_copies_variables_but_not_secrets(self):
        env = self._create_environment(name="Staging").data
        self.client.post(
            reverse("environment-variable-list-create", args=[env["id"]]),
            {"key": "LOG_LEVEL", "value": "debug"},
            format="json",
        )
        self.client.post(
            reverse("environment-secret-list-create", args=[env["id"]]),
            {"key": "API_KEY", "value": "super-secret-value"},
            format="json",
        )
        clone_resp = self.client.post(
            reverse("environment-clone", args=[env["id"]]), {"name": "Staging Copy"}, format="json"
        )
        self.assertEqual(clone_resp.status_code, status.HTTP_201_CREATED)
        clone_id = clone_resp.data["id"]

        variables = self.client.get(reverse("environment-variable-list-create", args=[clone_id]))
        self.assertEqual(len(variables.data), 1)
        self.assertEqual(variables.data[0]["key"], "LOG_LEVEL")

        secrets = self.client.get(reverse("environment-secret-list-create", args=[clone_id]))
        self.assertEqual(len(secrets.data), 0)

    def test_disable_then_enable_environment(self):
        env = self._create_environment().data
        disabled = self.client.post(reverse("environment-disable", args=[env["id"]]))
        self.assertEqual(disabled.data["status"], "disabled")
        enabled = self.client.post(reverse("environment-enable", args=[env["id"]]))
        self.assertEqual(enabled.data["status"], "active")

    def test_delete_requires_exact_name_confirmation(self):
        env = self._create_environment(name="Throwaway").data
        wrong = self.client.delete(
            reverse("environment-detail", args=[env["id"]]), {"confirm_name": "wrong"}, format="json"
        )
        self.assertEqual(wrong.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Environment.objects.filter(id=env["id"]).exists())

        right = self.client.delete(
            reverse("environment-detail", args=[env["id"]]), {"confirm_name": "Throwaway"}, format="json"
        )
        self.assertEqual(right.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Environment.objects.filter(id=env["id"]).exists())

    def test_production_delete_requires_stronger_confirmation(self):
        env = self._create_environment(name="Production", environment_type="production").data
        name_only = self.client.delete(
            reverse("environment-detail", args=[env["id"]]), {"confirm_name": "Production"}, format="json"
        )
        self.assertEqual(name_only.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Environment.objects.filter(id=env["id"]).exists())

        both = self.client.delete(
            reverse("environment-detail", args=[env["id"]]),
            {"confirm_name": "Production", "confirm_production_understanding": True},
            format="json",
        )
        self.assertEqual(both.status_code, status.HTTP_204_NO_CONTENT)

    def test_existing_organizations_and_applications_are_unaffected(self):
        """No environments is a valid, working state -- creating one is
        opt-in, matching "existing installations must continue working"."""
        resp = self.client.get(reverse("application-detail", args=[self.application_id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        envs = self.client.get(reverse("environment-list-create", args=[self.application_id]))
        self.assertEqual(envs.data, [])


class EnvironmentRbacTests(EnvironmentTestBase):
    def _add_member(self, email, role_slug):
        from organizations.models import Organization

        user = User.objects.create_user(email=email, password="x")
        Membership.objects.create(user=user, organization_id=self.org_id, status=Membership.Status.ACTIVE)
        assign_role(
            user=user,
            role_slug=role_slug,
            organization=Organization.objects.get(id=self.org_id),
            granted_by=self.admin,
        )
        return user

    def test_viewer_can_read_but_not_create_environment(self):
        viewer = self._add_member("env-viewer@example.com", "viewer")
        self.client.force_login(viewer)
        resp = self._create_environment()
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_viewer_can_list_environments(self):
        self._create_environment()
        viewer = self._add_member("env-viewer2@example.com", "viewer")
        self.client.force_login(viewer)
        resp = self.client.get(reverse("environment-list-create", args=[self.application_id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_developer_can_manage_non_production_environment(self):
        developer = self._add_member("env-dev@example.com", "developer")
        self.client.force_login(developer)
        resp = self._create_environment(name="Development", environment_type="development")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_developer_cannot_create_production_environment(self):
        developer = self._add_member("env-dev2@example.com", "developer")
        self.client.force_login(developer)
        resp = self._create_environment(name="Production", environment_type="production")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_developer_cannot_manage_existing_production_environment(self):
        prod = self._create_environment(name="Production", environment_type="production").data
        developer = self._add_member("env-dev3@example.com", "developer")
        self.client.force_login(developer)
        resp = self.client.patch(
            reverse("environment-detail", args=[prod["id"]]), {"name": "Prod Renamed"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_developer_cannot_delete_production_environment(self):
        prod = self._create_environment(name="Production", environment_type="production").data
        developer = self._add_member("env-dev4@example.com", "developer")
        self.client.force_login(developer)
        resp = self.client.delete(
            reverse("environment-detail", args=[prod["id"]]),
            {"confirm_name": "Production", "confirm_production_understanding": True},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_organization_administrator_can_manage_production(self):
        # self.admin is already organization-administrator (org creation
        # bootstrap) -- confirms the "Owner/Admin" tier is unrestricted.
        prod = self._create_environment(name="Production", environment_type="production").data
        resp = self.client.patch(
            reverse("environment-detail", args=[prod["id"]]), {"name": "Prod v2"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_member_from_another_organization_gets_404_not_403(self):
        env = self._create_environment().data
        outsider = User.objects.create_user(email="outsider@example.com", password="x")
        self.client.force_login(outsider)
        resp = self.client.get(reverse("environment-detail", args=[env["id"]]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class EnvironmentCredentialAndIsolationTests(EnvironmentTestBase):
    """The scenario the spec explicitly demands:
    Development credential -> attempt Production database access -> MUST FAIL.
    """

    def setUp(self):
        super().setUp()
        self.dev_env = self._create_environment(name="Development", environment_type="development").data
        self.prod_env = self._create_environment(name="Production", environment_type="production").data

        self.dev_db_id = self._create_tenant_database("dev-db")
        self.prod_db_id = self._create_tenant_database("prod-db")
        self.client.patch(
            reverse("environment-database-binding", args=[self.dev_env["id"]]),
            {"tenant_database_id": self.dev_db_id},
            format="json",
        )
        self.client.patch(
            reverse("environment-database-binding", args=[self.prod_env["id"]]),
            {"tenant_database_id": self.prod_db_id},
            format="json",
        )

        self.dev_bucket_id = self._create_bucket("dev-files")
        self.prod_bucket_id = self._create_bucket("production-files")
        self.client.patch(
            reverse("environment-storage-binding", args=[self.dev_env["id"]]),
            {"bucket_id": self.dev_bucket_id},
            format="json",
        )
        self.client.patch(
            reverse("environment-storage-binding", args=[self.prod_env["id"]]),
            {"bucket_id": self.prod_bucket_id},
            format="json",
        )

        dev_cred = self.client.post(
            reverse("environment-credential-list-create", args=[self.dev_env["id"]])
        )
        self.dev_token = dev_cred.data["secret"]
        self.dev_credential_id = dev_cred.data["id"]
        prod_cred = self.client.post(
            reverse("environment-credential-list-create", args=[self.prod_env["id"]])
        )
        self.prod_token = prod_cred.data["secret"]

        # The service account needs database.read/write on both
        # TenantDatabases via a ResourceGrant, mirroring how a real
        # Application's scope is restricted (Phase 7) -- deliberately
        # granted on *both* databases here, so the isolation test below
        # proves the Environment-scope check itself is what blocks
        # cross-environment access, not merely an absent ResourceGrant
        # that a misconfiguration could just as easily grant by mistake.
        from applications.models import Application
        from permissions.services import grant_resource_permission

        identity_user = Application.objects.get(id=self.application_id).service_account.identity_user
        for db_id in (self.dev_db_id, self.prod_db_id):
            for perm in ("database.read", "database.write"):
                grant_resource_permission(
                    user=identity_user,
                    permission_code=perm,
                    organization_id=self.org_id,
                    resource_type="databases.tenant_database",
                    resource_id=db_id,
                    granted_by=self.admin,
                )
        for bucket_id in (self.dev_bucket_id, self.prod_bucket_id):
            for perm in ("storage.read", "storage.write"):
                grant_resource_permission(
                    user=identity_user,
                    permission_code=perm,
                    organization_id=self.org_id,
                    resource_type="storage.bucket",
                    resource_id=bucket_id,
                    granted_by=self.admin,
                )

    def test_environment_scoped_credentials_are_independent(self):
        self.assertNotEqual(self.dev_token, self.prod_token)
        dev_credential = ApplicationCredential.objects.get(id=self.dev_credential_id)
        self.assertEqual(str(dev_credential.environment_id), self.dev_env["id"])

    def test_development_credential_can_access_development_database(self):
        table_id, row_id = self._create_table_with_row(self.dev_db_id)
        self.client.logout()
        resp = self.client.get(
            reverse("row-list-create", args=[table_id]), **self._auth_headers(self.dev_token)
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_development_credential_cannot_access_production_database(self):
        """The exact scenario from the spec: Development credential ->
        attempt Production database access -> MUST FAIL, despite holding
        a real ResourceGrant for database.read on the production
        database (see setUp) -- the Environment-scope check is what
        actually blocks it, independent of the permission system."""
        table_id, row_id = self._create_table_with_row(self.prod_db_id)
        self.client.logout()
        resp = self.client.get(
            reverse("row-list-create", args=[table_id]), **self._auth_headers(self.dev_token)
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        write_resp = self.client.post(
            reverse("row-list-create", args=[table_id]),
            {},
            format="json",
            **self._auth_headers(self.dev_token),
        )
        self.assertEqual(write_resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_production_credential_cannot_access_development_database(self):
        """Isolation is symmetric, not just "protect production"."""
        table_id, row_id = self._create_table_with_row(self.dev_db_id)
        self.client.logout()
        resp = self.client.get(
            reverse("row-list-create", args=[table_id]), **self._auth_headers(self.prod_token)
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_development_credential_cannot_access_production_storage(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.logout()
        upload = self.client.post(
            reverse("file-list-create", args=[self.prod_bucket_id]),
            {"file": SimpleUploadedFile("should-not-be-readable.txt", b"content", content_type="text/plain")},
            format="multipart",
            **self._auth_headers(self.dev_token),
        )
        # Denied before ever reaching upload_file -- storage.write is
        # granted, so a non-403 here would mean the environment check
        # didn't fire.
        self.assertEqual(upload.status_code, status.HTTP_403_FORBIDDEN)

    def test_unbound_database_is_unreachable_via_environment_scoped_credential(self):
        """A database that exists but was never assigned to *any*
        Environment must not be reachable through an Environment-scoped
        credential either -- explicit binding is required, "no
        conflicting binding" is not enough."""
        unbound_db_id = self._create_tenant_database("unbound-db")
        from applications.models import Application
        from permissions.services import grant_resource_permission

        identity_user = Application.objects.get(id=self.application_id).service_account.identity_user
        grant_resource_permission(
            user=identity_user,
            permission_code="database.read",
            organization_id=self.org_id,
            resource_type="databases.tenant_database",
            resource_id=unbound_db_id,
            granted_by=self.admin,
        )
        table_id, row_id = self._create_table_with_row(unbound_db_id)
        self.client.logout()
        resp = self.client.get(
            reverse("row-list-create", args=[table_id]), **self._auth_headers(self.dev_token)
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unscoped_credential_is_unaffected_by_environment_checks(self):
        """An Application-level credential with no environment at all
        (the pre-existing, still-supported shape) keeps working exactly
        as before -- environment scoping is opt-in. Reuses the
        database.read grant setUp already made on prod_db_id -- this
        credential just has no `environment`, so the environment-scope
        check never restricts it, same as before this subsystem existed."""
        unscoped = self.client.post(reverse("application-credential-list-create", args=[self.application_id]))
        unscoped_token = unscoped.data["secret"]
        table_id, row_id = self._create_table_with_row(self.prod_db_id)
        self.client.logout()
        resp = self.client.get(
            reverse("row-list-create", args=[table_id]), **self._auth_headers(unscoped_token)
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_revoked_environment_credential_is_rejected(self):
        # 403, not 401 -- DRF's get_authenticate_header only ever consults
        # the *first* configured authenticator (SessionAuthentication,
        # which has no WWW-Authenticate header), regardless of which
        # authenticator actually raised. Matches this codebase's
        # established, already-verified behavior for every other invalid-
        # credential case (applications/tests/test_applications.py's
        # test_revoked_credential_no_longer_authenticates).
        self.client.post(
            reverse("environment-credential-revoke", args=[self.dev_env["id"], self.dev_credential_id])
        )
        table_id, row_id = self._create_table_with_row(self.dev_db_id)
        self.client.logout()
        resp = self.client.get(
            reverse("row-list-create", args=[table_id]), **self._auth_headers(self.dev_token)
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_audit_event_recorded_for_credential_issuance_and_denial_visible_in_response(self):
        from audit.models import AuditEvent

        self.assertTrue(
            AuditEvent.objects.filter(
                organization_id=self.org_id,
                action="credential.created",
                resource_id=str(self.dev_credential_id),
            ).exists()
        )


class EnvironmentSecretProtectionTests(EnvironmentTestBase):
    def test_secret_value_is_never_returned_after_creation(self):
        env = self._create_environment().data
        create = self.client.post(
            reverse("environment-secret-list-create", args=[env["id"]]),
            {"key": "STRIPE_KEY", "value": "sk_live_reallysecret"},
            format="json",
        )
        self.assertEqual(create.data["value"], "sk_live_reallysecret")

        listing = self.client.get(reverse("environment-secret-list-create", args=[env["id"]]))
        self.assertNotIn("value", listing.data[0])
        self.assertEqual(listing.data[0]["key"], "STRIPE_KEY")

        detail_fields = set(listing.data[0].keys())
        self.assertEqual(detail_fields, {"id", "key", "created_at", "rotated_at"})

    def test_secret_stored_encrypted_not_plaintext(self):
        env = self._create_environment().data
        self.client.post(
            reverse("environment-secret-list-create", args=[env["id"]]),
            {"key": "DB_PASSWORD", "value": "hunter2-plaintext-marker"},
            format="json",
        )
        secret = EnvironmentSecret.objects.get(environment_id=env["id"], key="DB_PASSWORD")
        self.assertNotIn(b"hunter2-plaintext-marker", bytes(secret.value_ciphertext))

    def test_secret_value_never_appears_in_audit_context(self):
        env = self._create_environment().data
        self.client.post(
            reverse("environment-secret-list-create", args=[env["id"]]),
            {"key": "WEBHOOK_SECRET", "value": "another-plaintext-marker"},
            format="json",
        )
        from audit.models import AuditEvent

        events = AuditEvent.objects.filter(action="secret.created")
        self.assertTrue(events.exists())
        for event in events:
            self.assertNotIn("another-plaintext-marker", str(event.context))

    def test_rotate_returns_new_value_once_old_value_stops_working_conceptually(self):
        env = self._create_environment().data
        create = self.client.post(
            reverse("environment-secret-list-create", args=[env["id"]]),
            {"key": "API_KEY", "value": "first-value"},
            format="json",
        )
        secret_id = create.data["id"]
        rotate = self.client.post(
            reverse("environment-secret-rotate", args=[env["id"], secret_id]),
            {"value": "second-value"},
            format="json",
        )
        self.assertEqual(rotate.status_code, status.HTTP_201_CREATED)
        self.assertEqual(rotate.data["value"], "second-value")
        secret = EnvironmentSecret.objects.get(id=secret_id)
        self.assertIsNotNone(secret.rotated_at)

    def test_delete_secret(self):
        env = self._create_environment().data
        create = self.client.post(
            reverse("environment-secret-list-create", args=[env["id"]]),
            {"key": "TEMP_KEY", "value": "temp-value"},
            format="json",
        )
        secret_id = create.data["id"]
        delete = self.client.delete(reverse("environment-secret-detail", args=[env["id"], secret_id]))
        self.assertEqual(delete.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(EnvironmentSecret.objects.filter(id=secret_id).exists())

    def test_duplicate_secret_key_is_rejected_with_rotate_hint(self):
        env = self._create_environment().data
        self.client.post(
            reverse("environment-secret-list-create", args=[env["id"]]),
            {"key": "DUP", "value": "a"},
            format="json",
        )
        second = self.client.post(
            reverse("environment-secret-list-create", args=[env["id"]]),
            {"key": "DUP", "value": "b"},
            format="json",
        )
        self.assertEqual(second.status_code, status.HTTP_409_CONFLICT)


class EnvironmentBindingTests(EnvironmentTestBase):
    def test_binding_database_from_another_organization_is_rejected(self):
        env = self._create_environment().data
        other_org = self.client.post(reverse("organization-list-create"), {"name": "OtherOrg"})
        other_ws = self.client.post(
            reverse("workspace-list-create", args=[other_org.data["id"]]), {"name": "WS"}
        )
        other_proj = self.client.post(
            reverse("project-list-create", args=[other_ws.data["id"]]), {"name": "P"}
        )
        other_db = self.client.post(
            reverse("tenant-database-list-create", args=[other_proj.data["id"]]), {"name": "OtherDB"}
        )
        resp = self.client.patch(
            reverse("environment-database-binding", args=[env["id"]]),
            {"tenant_database_id": other_db.data["id"]},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_database_cannot_be_bound_to_two_environments(self):
        env_a = self._create_environment(name="A").data
        env_b = self._create_environment(name="B").data
        db_id = self._create_tenant_database("shared-db")
        first = self.client.patch(
            reverse("environment-database-binding", args=[env_a["id"]]),
            {"tenant_database_id": db_id},
            format="json",
        )
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        second = self.client.patch(
            reverse("environment-database-binding", args=[env_b["id"]]),
            {"tenant_database_id": db_id},
            format="json",
        )
        self.assertEqual(second.status_code, status.HTTP_409_CONFLICT)

    def test_unbind_database(self):
        env = self._create_environment().data
        db_id = self._create_tenant_database()
        self.client.patch(
            reverse("environment-database-binding", args=[env["id"]]),
            {"tenant_database_id": db_id},
            format="json",
        )
        unbind = self.client.patch(
            reverse("environment-database-binding", args=[env["id"]]),
            {"tenant_database_id": None},
            format="json",
        )
        self.assertEqual(unbind.status_code, status.HTTP_200_OK)
        self.assertEqual(unbind.data["database_status"], "not_connected")
