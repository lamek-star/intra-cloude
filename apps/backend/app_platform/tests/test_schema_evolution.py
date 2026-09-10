import uuid

from django.core.management import call_command
from django.db import connections
from django.test import TransactionTestCase
from psycopg import sql
from rest_framework.test import APIClient

from accounts.models import User
from app_platform import instances, provisioning, templates
from app_platform.models import FieldDefinition, ModelDefinition
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for, sample
from organizations.models import Membership
from organizations.services import create_organization
from permissions.services import assign_role, grant_resource_permission
from sharing.services import create_share_grant


class SchemaEvolutionTests(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="evolve-owner@example.com")
        self.org = create_organization(name="Evolve Org", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        template = templates.create_template(self.actor, self.org, {"label": "App", "draft": sample()})
        version = templates.publish_template(self.actor, template)
        self.instance = instances.install(
            self.actor, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )
        self.plan = plan_runtime(self.actor, self.instance)
        provisioning.reserve(self.actor, self.instance, self.plan["fingerprint"])
        self.receipt = provisioning.execute(self.instance.id, self.actor)
        self.item = self.instance.models.get(key="item")
        self.group = self.instance.models.get(key="group")
        self.client = APIClient()
        self.client.force_authenticate(self.actor)

    def tearDown(self):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.plan["schema_name"]))
            )
        super().tearDown()

    def add_field(self, model_id, payload):
        return self.client.post(f"/api/v1/app-models/{model_id}/fields/", payload, format="json")

    def test_adding_a_field_to_a_provisioned_model_applies_live_ddl(self):
        response = self.add_field(self.item.id, {"key": "sku", "label": "SKU", "data_type": "text"})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIn("position", response.data)
        field = FieldDefinition.objects.get(pk=response.data["id"])

        create = self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/", {str(field.id): "ABC-123"}, format="json"
        )
        self.assertEqual(create.status_code, 201, create.data)
        self.assertEqual(create.data[str(field.id)], "ABC-123")

    def test_adding_a_required_field_without_default_to_a_populated_model_is_rejected(self):
        name_field = self.item.fields.get(key="name")
        create = self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/", {str(name_field.id): "Existing"}, format="json"
        )
        self.assertEqual(create.status_code, 201, create.data)

        response = self.add_field(
            self.item.id, {"key": "urgent", "label": "Urgent", "data_type": "boolean", "required": True}
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(self.item.fields.filter(key="urgent").exists())

    def test_adding_a_required_field_with_default_backfills_existing_rows(self):
        name_field = self.item.fields.get(key="name")
        create = self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/", {str(name_field.id): "Existing"}, format="json"
        )
        self.assertEqual(create.status_code, 201, create.data)
        record_id = create.data["id"]

        response = self.add_field(
            self.item.id,
            {
                "key": "urgent",
                "label": "Urgent",
                "data_type": "boolean",
                "required": True,
                "default_value": False,
            },
        )
        self.assertEqual(response.status_code, 201, response.data)
        urgent_field = FieldDefinition.objects.get(pk=response.data["id"])

        existing = self.client.get(f"/api/v1/app-models/{self.item.id}/records/{record_id}/")
        self.assertEqual(existing.status_code, 200, existing.data)
        self.assertEqual(existing.data[str(urgent_field.id)], False)

    def test_adding_a_model_to_a_provisioned_instance_creates_a_working_table(self):
        response = self.client.post(
            f"/api/v1/app-instances/{self.instance.id}/models/", {"key": "vendor", "label": "Vendor"}
        )
        self.assertEqual(response.status_code, 201, response.data)
        vendor = ModelDefinition.objects.get(pk=response.data["id"])

        create = self.client.post(f"/api/v1/app-models/{vendor.id}/records/", {}, format="json")
        self.assertEqual(create.status_code, 201, create.data)

    def test_adding_a_relationship_enforces_a_real_foreign_key(self):
        group_field = self.client.post(
            f"/api/v1/app-instances/{self.instance.id}/relationships/",
            {
                "key": "backup_group",
                "label": "Backup group",
                "source_model": str(self.item.id),
                "target_model": str(self.group.id),
            },
            format="json",
        )
        self.assertEqual(group_field.status_code, 201, group_field.data)

        real_group = self.client.post(f"/api/v1/app-models/{self.group.id}/records/", {}, format="json")
        self.assertEqual(real_group.status_code, 201, real_group.data)

        ok = self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/",
            {group_field.data["id"]: real_group.data["id"]},
            format="json",
        )
        self.assertEqual(ok.status_code, 201, ok.data)

        rejected = self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/",
            {group_field.data["id"]: str(uuid.uuid4())},
            format="json",
        )
        self.assertEqual(rejected.status_code, 400, rejected.data)
        self.assertIn("referenced record does not exist", rejected.data["detail"])

    def test_live_addition_requires_database_schema_manage_once_provisioned(self):
        member = User.objects.create_user(email="evolve-member@example.com")
        Membership.objects.create(user=member, organization=self.org, status=Membership.Status.ACTIVE)
        grant_resource_permission(
            user=member,
            permission_code="app_instance.schema.manage",
            organization_id=self.org.id,
            resource_type="app_instance",
            resource_id=self.instance.id,
        )
        client = APIClient()
        client.force_authenticate(member)

        denied = client.post(
            f"/api/v1/app-models/{self.item.id}/fields/",
            {"key": "note", "label": "Note", "data_type": "text"},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)
        self.assertFalse(self.item.fields.filter(key="note").exists())

        # database.schema.manage is checked organization-wide only, never
        # resource-scoped, matching provisioning's own require_provision --
        # a schema-only app grant must never substitute for it.
        assign_role(user=member, role_slug="database-administrator", organization=self.org)
        allowed = client.post(
            f"/api/v1/app-models/{self.item.id}/fields/",
            {"key": "note", "label": "Note", "data_type": "text"},
            format="json",
        )
        self.assertEqual(allowed.status_code, 201, allowed.data)

    def test_admin_level_app_instance_share_does_not_substitute_for_database_schema_manage(self):
        """Phase 3 step 4 lets an app instance be shared at "admin" level
        (sharing.services.LEVEL_PERMISSIONS), which grants
        app_instance.schema.manage resource-scoped to that instance -- the
        same permission a direct ResourceGrant already proved insufficient
        above. Confirms the sharing integration doesn't accidentally widen
        that boundary: database.schema.manage must still come from a real
        organization-wide role."""
        member = User.objects.create_user(email="evolve-shared@example.com")
        Membership.objects.create(user=member, organization=self.org, status=Membership.Status.ACTIVE)
        create_share_grant(
            actor=self.actor,
            organization=self.org,
            resource_type="app_instance",
            resource_id=self.instance.id,
            principal_type="user",
            user=member,
            level="admin",
        )
        client = APIClient()
        client.force_authenticate(member)

        denied = client.post(
            f"/api/v1/app-models/{self.item.id}/fields/",
            {"key": "note", "label": "Note", "data_type": "text"},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)
        self.assertFalse(self.item.fields.filter(key="note").exists())

    def test_unresolved_provisioning_blocks_additions(self):
        definition = sample()
        template = templates.create_template(
            self.actor, self.org, {"label": "Pending App", "draft": definition}
        )
        version = templates.publish_template(self.actor, template)
        pending_instance = instances.install(
            self.actor, self.project, {"label": "Pending runtime", "template_version": str(version.id)}
        )
        pending_plan = plan_runtime(self.actor, pending_instance)
        provisioning.reserve(self.actor, pending_instance, pending_plan["fingerprint"])
        # Deliberately never call provisioning.execute() -- the receipt
        # stays unresolved (reserved, not completed).
        try:
            pending_item = pending_instance.models.get(key="item")
            response = self.add_field(pending_item.id, {"key": "sku", "label": "SKU", "data_type": "text"})
            self.assertEqual(response.status_code, 400, response.data)
        finally:
            with connections["tenant"].cursor() as cursor:
                cursor.execute(
                    sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                        sql.Identifier(pending_plan["schema_name"])
                    )
                )

    def test_existing_field_edits_stay_blocked_once_provisioned(self):
        name_field = self.item.fields.get(key="name")
        response = self.client.patch(
            f"/api/v1/app-fields/{name_field.id}/", {"required": True}, format="json"
        )
        self.assertEqual(response.status_code, 400, response.data)
        name_field.refresh_from_db()
        self.assertFalse(name_field.required)

    def test_adding_a_field_to_one_instance_does_not_affect_a_sibling_instance(self):
        template = templates.create_template(
            self.actor, self.org, {"label": "Sibling App", "draft": sample()}
        )
        version = templates.publish_template(self.actor, template)
        sibling = instances.install(
            self.actor, self.project, {"label": "Sibling runtime", "template_version": str(version.id)}
        )
        sibling_plan = plan_runtime(self.actor, sibling)
        provisioning.reserve(self.actor, sibling, sibling_plan["fingerprint"])
        provisioning.execute(sibling.id, self.actor)
        try:
            sibling_item = sibling.models.get(key="item")
            before = sibling_item.fields.count()

            response = self.add_field(self.item.id, {"key": "sku", "label": "SKU", "data_type": "text"})
            self.assertEqual(response.status_code, 201, response.data)

            self.assertEqual(sibling_item.fields.count(), before)
            self.assertFalse(sibling_item.fields.filter(key="sku").exists())
        finally:
            with connections["tenant"].cursor() as cursor:
                cursor.execute(
                    sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                        sql.Identifier(sibling_plan["schema_name"])
                    )
                )
