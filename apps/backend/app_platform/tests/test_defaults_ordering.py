from django.core.management import call_command
from django.db import connections
from django.test import TestCase, TransactionTestCase
from psycopg import sql
from rest_framework.test import APIClient

from accounts.models import User
from app_platform import instances, provisioning, templates
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for, sample
from databases import rows
from databases.models import DBTable
from organizations.services import create_organization


class DefinitionDefaultAndPositionTests(TestCase):
    """Metadata-only: no tenant DDL, so a plain TestCase is enough (matches
    FoundationTests' own choice for the same reason)."""

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="defaults-owner@example.com")
        self.org = create_organization(name="Defaults Org", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        template = templates.create_template(self.actor, self.org, {"label": "App", "draft": sample()})
        version = templates.publish_template(self.actor, template)
        self.instance = instances.install(
            self.actor, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )
        self.item = self.instance.models.get(key="item")
        self.client = APIClient()
        self.client.force_authenticate(self.actor)

    def test_default_value_is_validated_against_data_type(self):
        text_field = self.item.fields.get(key="name")
        decimal_field = self.item.fields.get(key="price")

        ok = self.client.patch(
            f"/api/v1/app-fields/{text_field.id}/", {"default_value": "untitled"}, format="json"
        )
        self.assertEqual(ok.status_code, 200, ok.data)
        self.assertEqual(ok.data["default_value"], "untitled")

        mismatched = self.client.patch(
            f"/api/v1/app-fields/{decimal_field.id}/", {"default_value": "not-a-number"}, format="json"
        )
        self.assertEqual(mismatched.status_code, 400, mismatched.data)

        wrong_type = self.client.patch(
            f"/api/v1/app-fields/{text_field.id}/", {"default_value": 5}, format="json"
        )
        self.assertEqual(wrong_type.status_code, 400, wrong_type.data)

    def test_new_model_field_relationship_append_to_the_end(self):
        second = self.client.post(
            f"/api/v1/app-instances/{self.instance.id}/models/", {"key": "vendor", "label": "Vendor"}
        )
        self.assertEqual(second.status_code, 201, second.data)
        self.assertEqual(second.data["position"], self.instance.models.count() - 1)

        third_field = self.client.post(
            f"/api/v1/app-models/{self.item.id}/fields/",
            {"key": "sku", "label": "SKU", "data_type": "text"},
        )
        self.assertEqual(third_field.status_code, 201, third_field.data)
        self.assertEqual(third_field.data["position"], self.item.fields.count() - 1)

    def test_position_can_be_reordered_and_fields_list_reflects_it(self):
        name_field = self.item.fields.get(key="name")
        price_field = self.item.fields.get(key="price")
        self.assertEqual(
            list(self.item.fields.values_list("key", flat=True)), ["name", "price"]
        )

        # Swap: move "price" before "name".
        r1 = self.client.patch(f"/api/v1/app-fields/{price_field.id}/", {"position": 0}, format="json")
        r2 = self.client.patch(f"/api/v1/app-fields/{name_field.id}/", {"position": 1}, format="json")
        self.assertEqual(r1.status_code, 200, r1.data)
        self.assertEqual(r2.status_code, 200, r2.data)
        self.assertEqual(
            list(self.item.fields.order_by("position", "created_at", "id").values_list("key", flat=True)),
            ["price", "name"],
        )

    def test_install_preserves_draft_array_order_as_position(self):
        definition = sample()
        # Prepend a third field so array order is meaningfully non-trivial.
        definition["models"][0]["fields"].insert(0, {"key": "sku", "label": "SKU", "data_type": "text"})
        template = templates.create_template(self.actor, self.org, {"label": "Ordered", "draft": definition})
        version = templates.publish_template(self.actor, template)
        instance = instances.install(
            self.actor, self.project, {"label": "Ordered app", "template_version": str(version.id)}
        )
        item = instance.models.get(key="item")
        self.assertEqual(list(item.fields.values_list("key", flat=True)), ["sku", "name", "price"])
        self.assertEqual(list(item.fields.values_list("position", flat=True)), [0, 1, 2])


class ProvisionedDefaultValueTests(TransactionTestCase):
    """Confirms a field default becomes a real Postgres COLUMN DEFAULT, not
    just definition metadata -- needs a real tenant schema."""

    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="defaults-provision@example.com")
        self.org = create_organization(name="Defaults Provision Org", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        definition = sample()
        definition["models"][0]["fields"][0]["default_value"] = "Untitled"
        definition["models"][0]["fields"].append(
            {"key": "active", "label": "Active", "data_type": "boolean", "default_value": True}
        )
        definition["models"][0]["fields"].append(
            {"key": "signup_date", "label": "Signup date", "data_type": "date", "default_value": "2026-01-01"}
        )
        template = templates.create_template(self.actor, self.org, {"label": "App", "draft": definition})
        version = templates.publish_template(self.actor, template)
        self.instance = instances.install(
            self.actor, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )
        self.plan = plan_runtime(self.actor, self.instance)
        provisioning.reserve(self.actor, self.instance, self.plan["fingerprint"])
        self.receipt = provisioning.execute(self.instance.id, self.actor)
        self.item = self.instance.models.get(key="item")
        self.client = APIClient()
        self.client.force_authenticate(self.actor)

    def tearDown(self):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.plan["schema_name"]))
            )
        super().tearDown()

    def test_omitted_fields_receive_their_defined_defaults(self):
        name_field = self.item.fields.get(key="name")
        active_field = self.item.fields.get(key="active")
        date_field = self.item.fields.get(key="signup_date")
        price_field = self.item.fields.get(key="price")

        url = f"/api/v1/app-models/{self.item.id}/records/"
        # Only "price" (no default) is supplied -- everything else must
        # come from the real column DEFAULT the provisioning step wrote.
        create = self.client.post(url, {str(price_field.id): "9.99"}, format="json")
        self.assertEqual(create.status_code, 201, create.data)
        self.assertEqual(create.data[str(name_field.id)], "Untitled")
        self.assertEqual(create.data[str(active_field.id)], True)
        self.assertEqual(str(create.data[str(date_field.id)]), "2026-01-01")

        table = DBTable.objects.get(pk=self.receipt.bindings["models"][str(self.item.id)])
        physical = rows.get_row(table, create.data["id"])
        self.assertEqual(physical[f"f_{name_field.id.hex}"], "Untitled")
        self.assertTrue(physical[f"f_{active_field.id.hex}"])
