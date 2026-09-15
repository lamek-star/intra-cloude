"""Post-Phase-3 Integration Enablement, Part 1: bearer-token
(`applications.ApplicationCredential`) access to App Platform. This is
the actual external-integration surface -- record CRUD, attachments, and
read-only schema/runtime discovery against an already-provisioned
instance -- authorized by the exact same deny-by-default
ResourceGrant/has_permission mechanism a human session uses (access.py),
reachable only where FoundationView.service_account_methods (views.py)
explicitly opts a method in. Nothing here is a second authentication or
authorization system; see docs/EXTERNAL_APP_API_CONTRACT.md."""

from django.core.management import call_command
from django.db import connections
from django.test import TransactionTestCase
from psycopg import sql
from rest_framework.test import APIClient

from accounts.models import User
from app_platform import instances, provisioning, templates
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for, sample
from applications import services as app_services
from audit.models import AuditEvent
from organizations.services import create_organization
from permissions.services import grant_resource_permission
from workspaces.models import Project, Workspace


class ExternalBearerAccessTests(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.owner = User.objects.create_user(email="ext-owner@example.com")
        self.org = create_organization(name="External Org", created_by=self.owner)
        self.project = project_for(self.owner, self.org)
        template = templates.create_template(self.owner, self.org, {"label": "App", "draft": sample()})
        version = templates.publish_template(self.owner, template)
        self.instance = instances.install(
            self.owner, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )
        self.plan = plan_runtime(self.owner, self.instance)
        provisioning.reserve(self.owner, self.instance, self.plan["fingerprint"])
        self.receipt = provisioning.execute(self.instance.id, self.owner)
        self.item = self.instance.models.get(key="item")
        self.name_field = self.item.fields.get(key="name")

        self.application = app_services.register_application(
            organization=self.org, name="Integration Bot", description="", owner=self.owner
        )
        self.credential, self.token = app_services.issue_credential(
            service_account=self.application.service_account, actor=self.owner
        )
        # Anonymous by default -- every request in this file authenticates
        # purely via the Authorization header, exactly like a real
        # external client, never force_authenticate (which would bypass
        # the actual bearer-token resolution path this feature adds).
        self.client = APIClient()

    def tearDown(self):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.plan["schema_name"]))
            )
        super().tearDown()

    def _auth(self, token=None):
        return {"HTTP_AUTHORIZATION": f"Bearer {token or self.token}"}

    def _grant_record_access(self, *, read=True, write=True):
        codes = []
        if read:
            codes.append("database.read")
        if write:
            codes.append("database.write")
        for code in codes:
            grant_resource_permission(
                user=self.application.service_account.identity_user,
                permission_code=code,
                organization_id=self.org.id,
                resource_type="databases.tenant_database",
                resource_id=self.receipt.database_id,
                granted_by=self.owner,
            )

    def _grant_instance_read(self):
        grant_resource_permission(
            user=self.application.service_account.identity_user,
            permission_code="app_instance.read",
            organization_id=self.org.id,
            resource_type="app_instance",
            resource_id=self.instance.id,
            granted_by=self.owner,
        )

    # 1. Valid external credential can access its authorized AppInstance.
    def test_valid_credential_reads_its_authorized_instance_and_records(self):
        self._grant_instance_read()
        self._grant_record_access()

        instance_resp = self.client.get(f"/api/v1/app-instances/{self.instance.id}/", **self._auth())
        self.assertEqual(instance_resp.status_code, 200, instance_resp.data)

        create = self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/",
            {str(self.name_field.id): "Widget"},
            format="json",
            **self._auth(),
        )
        self.assertEqual(create.status_code, 201, create.data)
        record_id = create.data["id"]

        read = self.client.get(f"/api/v1/app-models/{self.item.id}/records/{record_id}/", **self._auth())
        self.assertEqual(read.status_code, 200)
        self.assertEqual(read.data[str(self.name_field.id)], "Widget")

    # 2. Credential cannot access another organization's AppInstance.
    def test_credential_cannot_access_another_organizations_instance(self):
        other_owner = User.objects.create_user(email="ext-other-owner@example.com")
        other_org = create_organization(name="Other Org", created_by=other_owner)
        other_project = project_for(other_owner, other_org)
        other_template = templates.create_template(
            other_owner, other_org, {"label": "Other App", "draft": sample()}
        )
        other_version = templates.publish_template(other_owner, other_template)
        other_instance = instances.install(
            other_owner, other_project, {"label": "Other Runtime", "template_version": str(other_version.id)}
        )
        # This credential belongs to self.org -- it was never made a
        # member of other_org, so even an (impossible in practice)
        # matching grant couldn't apply; get_owned's own org-membership
        # filter is the thing actually enforcing this.
        resp = self.client.get(f"/api/v1/app-instances/{other_instance.id}/", **self._auth())
        self.assertEqual(resp.status_code, 404)

    # 3. Credential cannot access an unrelated project (same org, no grant).
    def test_credential_cannot_access_an_unrelated_project_instance(self):
        self._grant_instance_read()
        self._grant_record_access()
        other_workspace = Workspace.objects.create(
            organization=self.org, name="Other Workspace", created_by=self.owner
        )
        other_project = Project.objects.create(
            workspace=other_workspace, name="Other Project", created_by=self.owner
        )
        other_template = templates.create_template(
            self.owner, self.org, {"label": "Sibling App", "draft": sample()}
        )
        other_version = templates.publish_template(self.owner, other_template)
        sibling_instance = instances.install(
            self.owner,
            other_project,
            {"label": "Sibling Runtime", "template_version": str(other_version.id)},
        )
        # Same organization, so get_owned() would find it -- only the
        # resource-scoped grant (never given for THIS instance) stands
        # between the credential and access.
        resp = self.client.get(f"/api/v1/app-instances/{sibling_instance.id}/", **self._auth())
        self.assertEqual(resp.status_code, 403)

    # 4. Revoked credential fails.
    def test_revoked_credential_fails(self):
        self._grant_instance_read()
        app_services.revoke_credential(credential=self.credential, actor=self.owner)
        resp = self.client.get(f"/api/v1/app-instances/{self.instance.id}/", **self._auth())
        self.assertEqual(resp.status_code, 403)

    # 5. Invalid token fails.
    def test_invalid_token_fails(self):
        resp = self.client.get(
            f"/api/v1/app-instances/{self.instance.id}/", HTTP_AUTHORIZATION="Bearer not-a-real-token"
        )
        self.assertEqual(resp.status_code, 403)

    # 6. Missing token fails for an external protected route.
    def test_missing_token_fails(self):
        resp = self.client.get(f"/api/v1/app-instances/{self.instance.id}/")
        self.assertIn(resp.status_code, (401, 403))

    # 7. Credential lacking the required capability fails.
    def test_credential_without_required_capability_fails(self):
        # No grants at all -- Membership (created by register_application)
        # alone grants nothing, matching every human-actor test elsewhere.
        resp = self.client.get(f"/api/v1/app-instances/{self.instance.id}/", **self._auth())
        self.assertEqual(resp.status_code, 403)

    # 8. Browser/session authentication continues working.
    def test_human_session_access_is_unaffected(self):
        human_client = APIClient()
        human_client.force_authenticate(self.owner)
        resp = human_client.get(f"/api/v1/app-instances/{self.instance.id}/")
        self.assertEqual(resp.status_code, 200)

    # 10. Audit correctly attributes external actions to the service
    # account's own identity, not the human who granted access.
    def test_audit_attributes_a_record_mutation_to_the_service_account_identity(self):
        self._grant_record_access()
        create = self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/",
            {str(self.name_field.id): "Audited"},
            format="json",
            **self._auth(),
        )
        self.assertEqual(create.status_code, 201, create.data)
        event = AuditEvent.objects.get(
            action="app_instance.record.create", resource_id=str(self.item.id)
        )
        self.assertEqual(event.actor_id, self.application.service_account.identity_user_id)
        self.assertNotEqual(event.actor_id, self.owner.id)

    # 11. Cross-tenant ID substitution is denied (a real record id from a
    # sibling instance's table, guessed against this credential's grant).
    def test_cross_instance_record_id_substitution_is_denied(self):
        self._grant_record_access()
        sibling_template = templates.create_template(
            self.owner, self.org, {"label": "Sibling App 2", "draft": sample()}
        )
        sibling_version = templates.publish_template(self.owner, sibling_template)
        sibling_instance = instances.install(
            self.owner,
            self.project,
            {"label": "Sibling Runtime 2", "template_version": str(sibling_version.id)},
        )
        sibling_plan = plan_runtime(self.owner, sibling_instance)
        provisioning.reserve(self.owner, sibling_instance, sibling_plan["fingerprint"])
        try:
            # No grant on the sibling's tenant database -- only this
            # instance's. The sibling model id itself must 404, not leak
            # a 403 that would confirm its existence.
            sibling_item = sibling_instance.models.get(key="item")
            resp = self.client.get(f"/api/v1/app-models/{sibling_item.id}/records/", **self._auth())
            self.assertEqual(resp.status_code, 404)
        finally:
            with connections["tenant"].cursor() as cursor:
                cursor.execute(
                    sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                        sql.Identifier(sibling_plan["schema_name"])
                    )
                )

    # 12. Token cannot escalate to template/platform administration, even
    # holding full record + instance-read access elsewhere.
    def test_full_record_access_does_not_escalate_to_template_or_install_administration(self):
        self._grant_instance_read()
        self._grant_record_access()
        grant_resource_permission(
            user=self.application.service_account.identity_user,
            permission_code="app_instance.manage",
            organization_id=self.org.id,
            resource_type="app_instance",
            resource_id=self.instance.id,
            granted_by=self.owner,
        )

        # PATCH on the instance itself: the capability is granted, but
        # the method was never opted into service_account_methods.
        rename = self.client.patch(
            f"/api/v1/app-instances/{self.instance.id}/", {"label": "Hijacked"}, format="json", **self._auth()
        )
        self.assertEqual(rename.status_code, 403)

        # Template administration: a completely separate view, never
        # opted in regardless of any grant.
        templates_list = self.client.get(
            f"/api/v1/organizations/{self.org.id}/app-templates/", **self._auth()
        )
        self.assertEqual(templates_list.status_code, 403)

        # Provisioning a fresh instance: administrative, human-only.
        install = self.client.post(
            f"/api/v1/projects/{self.project.id}/app-instances/",
            {"template_version": str(self.receipt.plan["fingerprint"])},
            format="json",
            **self._auth(),
        )
        self.assertEqual(install.status_code, 403)

    def test_attachment_access_requires_the_same_record_capability(self):
        self._grant_record_access()
        create = self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/",
            {str(self.name_field.id): "With attachment"},
            format="json",
            **self._auth(),
        )
        record_id = create.data["id"]
        listing = self.client.get(
            f"/api/v1/app-models/{self.item.id}/records/{record_id}/attachments/", **self._auth()
        )
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data, [])

    def test_runtime_status_readable_but_provisioning_stays_human_only(self):
        grant_resource_permission(
            user=self.application.service_account.identity_user,
            permission_code="app_instance.schema.manage",
            organization_id=self.org.id,
            resource_type="app_instance",
            resource_id=self.instance.id,
            granted_by=self.owner,
        )
        status_resp = self.client.get(f"/api/v1/app-instances/{self.instance.id}/runtime/", **self._auth())
        self.assertEqual(status_resp.status_code, 200, status_resp.data)
        self.assertEqual(status_resp.data["status"], "ready")

        provision = self.client.post(
            f"/api/v1/app-instances/{self.instance.id}/runtime/",
            {"fingerprint": self.plan["fingerprint"]},
            format="json",
            **self._auth(),
        )
        self.assertEqual(provision.status_code, 403)
