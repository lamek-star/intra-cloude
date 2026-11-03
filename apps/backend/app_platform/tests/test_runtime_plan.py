import copy
import uuid

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from accounts.models import User
from app_platform import instances, templates
from app_platform.definitions import validate_definition
from app_platform.runtime_plan import compile_plan, plan_runtime
from app_platform.tests.test_foundation import project_for, sample
from databases.models import TenantDatabase
from organizations.models import Membership
from organizations.services import create_organization
from permissions.services import grant_resource_permission


class PlanCompilerTests(SimpleTestCase):
    def setUp(self):
        self.identity = uuid.uuid4()
        self.definition = validate_definition(sample())

    def test_names_and_fingerprint_survive_label_and_order_changes(self):
        before = compile_plan(self.identity, self.definition)
        self.definition["models"].reverse()
        for model in self.definition["models"]:
            model["label"] = "A new display name"
            model["fields"].reverse()
            for field in model["fields"]:
                field["label"] = "Renamed"
        self.assertEqual(before, compile_plan(self.identity, self.definition))

    def test_field_and_relationship_keys_can_overlap_without_physical_collision(self):
        definition = copy.deepcopy(self.definition)
        definition["relationships"][0]["key"] = "name"
        plan = compile_plan(self.identity, definition)
        names = [column["name"] for model in plan["models"] for column in model["columns"]]
        names += [relation["column"] for relation in plan["relationships"]]
        self.assertEqual(len(names), len(set(names)))
        for name in names:
            self.assertRegex(name, r"^[fr]_[0-9a-f]{32}$")

    def test_required_and_relationship_policy_change_the_fingerprint(self):
        before = compile_plan(self.identity, self.definition)["fingerprint"]
        self.definition["models"][0]["fields"][0]["required"] = True
        required = compile_plan(self.identity, self.definition)["fingerprint"]
        self.assertNotEqual(before, required)
        self.definition["relationships"][0]["deletion_policy"] = "set_null"
        self.assertNotEqual(required, compile_plan(self.identity, self.definition)["fingerprint"])

    def test_instances_have_different_databases_even_for_identical_definitions(self):
        first = compile_plan(self.identity, self.definition)
        second = compile_plan(uuid.uuid4(), self.definition)
        self.assertNotEqual(first["database_id"], second["database_id"])
        self.assertNotEqual(first["schema_name"], second["schema_name"])

    def test_decimal_and_reference_contract(self):
        plan = compile_plan(self.identity, self.definition)
        decimal = next(
            column for model in plan["models"] for column in model["columns"]
            if column["data_type"] == "decimal"
        )
        self.assertEqual((decimal["precision"], decimal["scale"]), (18, 4))
        self.assertTrue(plan["relationships"][0]["is_nullable"])
        self.assertEqual(plan["relationships"][0]["on_delete"], "restrict")

    def test_invalid_definition_is_rejected_before_compilation(self):
        cases = []
        bad = copy.deepcopy(self.definition)
        bad["models"][0]["key"] = 'item; DROP SCHEMA public CASCADE'
        cases.append(bad)
        bad = copy.deepcopy(self.definition)
        bad["relationships"][0]["target_model"] = str(uuid.uuid4())
        cases.append(bad)
        bad = copy.deepcopy(self.definition)
        bad["models"][0]["fields"][0]["data_type"] = "sql"
        cases.append(bad)
        cases.append({"schema_version": 1, "models": [], "relationships": []})
        for definition in cases:
            with self.subTest(definition=definition), self.assertRaises(ValidationError):
                compile_plan(self.identity, definition)


class RuntimePlanAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_permissions", verbosity=0)
        cls.owner = User.objects.create_user(email="runtime-owner@example.com")
        cls.member = User.objects.create_user(email="runtime-member@example.com")
        cls.outsider = User.objects.create_user(email="runtime-outsider@example.com")
        cls.org = create_organization(name="Runtime Org", created_by=cls.owner)
        Membership.objects.create(user=cls.member, organization=cls.org, status="active")
        cls.project = project_for(cls.owner, cls.org)
        template = templates.create_template(cls.owner, cls.org, {"label": "Plan", "draft": sample()})
        version = templates.publish_template(cls.owner, template)
        cls.instance = instances.install(
            cls.owner, cls.project, {"template_version": str(version.id), "label": "Runtime"}
        )
        cls.url = f"/api/v1/app-instances/{cls.instance.id}/runtime-plan/"

    def setUp(self):
        self.client = APIClient()

    def test_owner_can_preview_without_creating_a_database(self):
        self.client.force_authenticate(self.owner)
        count = TenantDatabase.objects.count()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["instance_id"], str(self.instance.id))
        self.assertEqual(response.data, plan_runtime(self.owner, self.instance))
        self.assertEqual(TenantDatabase.objects.count(), count)
        self.assertEqual(self.client.post(self.url, {}, format="json").status_code, 405)

    def test_organization_boundary_and_missing_membership(self):
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.client.force_authenticate(self.member)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_exact_schema_grant_and_revocation(self):
        grant = grant_resource_permission(
            user=self.member, permission_code="app_instance.schema.manage", organization_id=self.org.id,
            resource_type="app_instance", resource_id=self.instance.id, granted_by=self.owner,
        )
        self.client.force_authenticate(self.member)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        grant.delete()
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_read_capability_is_not_schema_authority(self):
        grant_resource_permission(
            user=self.member, permission_code="app_instance.read", organization_id=self.org.id,
            resource_type="app_instance", resource_id=self.instance.id, granted_by=self.owner,
        )
        self.client.force_authenticate(self.member)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_archived_instance_cannot_be_planned(self):
        instances.update_instance(self.owner, self.instance, {"archived": True})
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get(self.url).status_code, 400)

    def test_anonymous_access_is_denied(self):
        self.assertIn(self.client.get(self.url).status_code, [401, 403])
