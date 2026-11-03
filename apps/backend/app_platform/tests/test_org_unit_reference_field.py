"""Phase 7 Step 1 -- the org_unit_reference field type (docs/implementation/
APP_PLATFORM_PHASE7.md): a business-record field that names an
org_units.OrganizationalUnit. Physically a plain UUID column with no real
Postgres FK (OrganizationalUnit lives in the control-plane database, the
record lives in a per-tenant database) -- existence and organization-match
are validated in app_platform/records.py instead, so this test file is
mostly about proving that validation actually rejects what a real FK
constraint would have caught for free."""

import uuid

from django.core.management import call_command
from django.db import connections
from django.test import TransactionTestCase
from psycopg import sql
from rest_framework.test import APIClient

from accounts.models import User
from app_platform import instances, provisioning, templates
from app_platform.runtime_plan import physical_data_type, plan_runtime
from app_platform.tests.test_foundation import project_for
from org_units.models import OrganizationalUnit
from organizations.services import create_organization


def org_unit_reference_sample():
    model_id = str(uuid.uuid4())
    return {
        "schema_version": 1,
        "models": [
            {
                "id": model_id,
                "key": "task",
                "label": "Task",
                "fields": [
                    {"key": "name", "label": "Name", "data_type": "text", "required": True},
                    {"key": "owning_unit", "label": "Owning Unit", "data_type": "org_unit_reference"},
                ],
            }
        ],
        "relationships": [],
    }


class PhysicalDataTypeTests(TransactionTestCase):
    databases = {"default"}

    def test_org_unit_reference_maps_to_a_physical_uuid_column(self):
        self.assertEqual(physical_data_type("org_unit_reference"), "uuid")

    def test_other_types_pass_through_unchanged(self):
        for data_type in ("text", "integer", "decimal", "boolean", "date", "datetime"):
            self.assertEqual(physical_data_type(data_type), data_type)


class OrgUnitReferenceRecordTests(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="oref-owner@example.com")
        self.org = create_organization(name="Org Unit Reference Org", created_by=self.actor)
        self.other_org = create_organization(name="Other Org", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        template = templates.create_template(
            self.actor, self.org, {"label": "App", "draft": org_unit_reference_sample()}
        )
        version = templates.publish_template(self.actor, template)
        self.instance = instances.install(
            self.actor, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )
        self.task = self.instance.models.get(key="task")
        self.name_field = self.task.fields.get(key="name")
        self.unit_field = self.task.fields.get(key="owning_unit")

        self.plan = plan_runtime(self.actor, self.instance)
        provisioning.reserve(self.actor, self.instance, self.plan["fingerprint"])
        self.receipt = provisioning.execute(self.instance.id, self.actor)

        self.unit = OrganizationalUnit.objects.create(
            organization=self.org, name="Warehouse A", unit_type="warehouse", created_by=self.actor
        )
        self.other_org_unit = OrganizationalUnit.objects.create(
            organization=self.other_org, name="Foreign Unit", unit_type="branch", created_by=self.actor
        )

        self.tasks_url = f"/api/v1/app-models/{self.task.id}/records/"
        self.client = APIClient()
        self.client.force_authenticate(self.actor)

    def tearDown(self):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.plan["schema_name"]))
            )
        super().tearDown()

    def detail_url(self, record_id):
        return f"{self.tasks_url}{record_id}/"

    def test_a_valid_unit_in_the_same_organization_is_accepted(self):
        resp = self.client.post(
            self.tasks_url,
            {str(self.name_field.id): "Fix the thing", str(self.unit_field.id): str(self.unit.id)},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(str(resp.data[str(self.unit_field.id)]), str(self.unit.id))

    def test_null_is_accepted_since_the_field_is_not_required(self):
        resp = self.client.post(
            self.tasks_url, {str(self.name_field.id): "No unit yet"}, format="json"
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertIsNone(resp.data[str(self.unit_field.id)])

    def test_a_unit_from_another_organization_is_rejected(self):
        resp = self.client.post(
            self.tasks_url,
            {
                str(self.name_field.id): "Cross-org attempt",
                str(self.unit_field.id): str(self.other_org_unit.id),
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.data)

    def test_a_nonexistent_unit_id_is_rejected(self):
        resp = self.client.post(
            self.tasks_url,
            {str(self.name_field.id): "Ghost unit", str(self.unit_field.id): str(uuid.uuid4())},
            format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.data)

    def test_a_malformed_value_is_rejected_cleanly_not_a_500(self):
        resp = self.client.post(
            self.tasks_url,
            {str(self.name_field.id): "Bad value", str(self.unit_field.id): "not-a-uuid"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.data)

    def test_update_also_validates_the_reference(self):
        created = self.client.post(
            self.tasks_url, {str(self.name_field.id): "Reassign me"}, format="json"
        )
        record_id = created.data["id"]

        good = self.client.patch(
            self.detail_url(record_id), {str(self.unit_field.id): str(self.unit.id)}, format="json"
        )
        self.assertEqual(good.status_code, 200, good.data)

        bad = self.client.patch(
            self.detail_url(record_id), {str(self.unit_field.id): str(self.other_org_unit.id)}, format="json"
        )
        self.assertEqual(bad.status_code, 400, bad.data)
        # The rejected update must not have overwritten the valid value.
        current = self.client.get(self.detail_url(record_id))
        self.assertEqual(str(current.data[str(self.unit_field.id)]), str(self.unit.id))


class LiveSchemaAdditionTests(TransactionTestCase):
    """Phase 3's safe-additive-schema-change path must accept this field
    type too, not just installation time."""

    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="oref-live-owner@example.com")
        self.org = create_organization(name="Live Org Unit Ref Org", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        model_id = str(uuid.uuid4())
        draft = {
            "schema_version": 1,
            "models": [
                {
                    "id": model_id,
                    "key": "task",
                    "label": "Task",
                    "fields": [{"key": "name", "label": "Name", "data_type": "text", "required": True}],
                }
            ],
            "relationships": [],
        }
        template = templates.create_template(self.actor, self.org, {"label": "App", "draft": draft})
        version = templates.publish_template(self.actor, template)
        self.instance = instances.install(
            self.actor, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )
        self.task = self.instance.models.get(key="task")
        self.plan = plan_runtime(self.actor, self.instance)
        provisioning.reserve(self.actor, self.instance, self.plan["fingerprint"])
        self.receipt = provisioning.execute(self.instance.id, self.actor)

        self.client = APIClient()
        self.client.force_authenticate(self.actor)

    def tearDown(self):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.plan["schema_name"]))
            )
        super().tearDown()

    def test_adding_an_org_unit_reference_field_live_succeeds_and_is_usable(self):
        add = self.client.post(
            f"/api/v1/app-models/{self.task.id}/fields/",
            {"key": "owning_unit", "label": "Owning Unit", "data_type": "org_unit_reference"},
            format="json",
        )
        self.assertEqual(add.status_code, 201, add.data)

        unit = OrganizationalUnit.objects.create(
            organization=self.org, name="New Unit", unit_type="team", created_by=self.actor
        )
        name_field = self.task.fields.get(key="name")
        record = self.client.post(
            f"/api/v1/app-models/{self.task.id}/records/",
            {str(name_field.id): "Uses the new field", add.data["id"]: str(unit.id)},
            format="json",
        )
        self.assertEqual(record.status_code, 201, record.data)
        self.assertEqual(str(record.data[add.data["id"]]), str(unit.id))
