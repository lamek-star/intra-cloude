"""The Pharmacy built-in application: the Spare Parts engine in its pharmacy edition
(reference_templates/pharmacy.py).

Proves the edition keeps the engine intact (same models, relationships and quantity ledger), that it is
offered only as a named pilot preview, and that an installed Pharmacy stores the medicine facts, imports a
medicine and its item number in one atomic transaction (as the catalogue import does), and still refuses to
sell stock it does not have. Cross-organization isolation is the App Platform pipeline's, already tested
(test_foundation.py); this template adds no endpoint or resource type.
"""

from django.core.management import call_command
from django.db import connections
from django.test import SimpleTestCase, TransactionTestCase, override_settings
from psycopg import sql
from rest_framework.test import APIClient

from accounts.models import User
from app_platform import built_in_apps
from app_platform.definitions import validate_definition
from app_platform.models import AppInstance, QuantityLedgerBinding, RuntimeProvision
from app_platform.reference_templates import pharmacy_reference_definition, spare_parts_reference_definition
from app_platform.reference_templates.pharmacy import MEDICINE_FIELDS
from app_platform.tests.test_foundation import project_for
from organizations.services import create_organization


class PharmacyDefinitionTests(SimpleTestCase):
    def test_it_is_the_spare_parts_engine_with_medicine_fields_on_the_product(self):
        pharmacy = validate_definition(pharmacy_reference_definition())
        spare = validate_definition(spare_parts_reference_definition())
        self.assertEqual([m["key"] for m in pharmacy["models"]], [m["key"] for m in spare["models"]])
        self.assertEqual(
            [r["key"] for r in pharmacy["relationships"]], [r["key"] for r in spare["relationships"]]
        )
        self.assertEqual(len(pharmacy["quantity_ledgers"]), 1)
        part = next(m for m in pharmacy["models"] if m["key"] == "part")
        keys = {f["key"] for f in part["fields"]}
        self.assertTrue({"name", "list_price", "standard_cost"} <= keys)
        self.assertTrue({key for key, *_ in MEDICINE_FIELDS} <= keys)
        self.assertEqual(part["label"], "Medicine")

    def test_ids_are_stable_and_distinct_from_spare_parts(self):
        a = built_in_apps.definition_for("pharmacy")
        b = built_in_apps.definition_for("pharmacy")
        self.assertEqual(a, b)
        spare_ids = {m["id"] for m in built_in_apps.definition_for("spare_parts")["models"]}
        self.assertFalse(spare_ids & {m["id"] for m in a["models"]})


class PharmacyVisibilityTests(SimpleTestCase):
    @override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=False, BUILT_IN_APP_PREVIEWS=[])
    def test_hidden_unless_named_as_a_preview(self):
        self.assertNotIn("pharmacy", {a["key"] for a in built_in_apps.listing()})

    @override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=False, BUILT_IN_APP_PREVIEWS=["pharmacy", "crm"])
    def test_a_named_preview_is_shown_with_its_honest_label_and_never_a_deferred_app(self):
        shown = {a["key"]: a for a in built_in_apps.listing()}
        self.assertEqual(shown["pharmacy"]["status_label"], "Pilot preview")
        self.assertNotIn("crm", shown)  # deferred: the preview list is not a way around that
        self.assertNotIn("hr", shown)  # only the named preview, not every experimental app


@override_settings(SHOW_UNQUALIFIED_BUILT_IN_APPS=False, BUILT_IN_APP_PREVIEWS=["pharmacy"])
class PharmacyInstallTests(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.owner = User.objects.create_user(email="pharmacy-owner@example.com")
        self.org = create_organization(name="Asmara Pharmacy", created_by=self.owner)
        self.project = project_for(self.owner, self.org)
        self.client = APIClient()
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            f"/api/v1/projects/{self.project.id}/built-in-apps/pharmacy/install/",
            {"label": "Pharmacy"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.instance = AppInstance.objects.get(pk=response.data["id"])

    def tearDown(self):
        with connections["tenant"].cursor() as cursor:
            for receipt in RuntimeProvision.objects.all():
                cursor.execute(
                    sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                        sql.Identifier(receipt.plan["schema_name"])
                    )
                )
        super().tearDown()

    def field(self, model_key, key):
        model = self.instance.models.get(key=model_key)
        found = model.fields.filter(key=key).first()
        return str(found.id if found else self.instance.relationships.get(key=key, source_model=model).id)

    def model(self, key):
        return str(self.instance.models.get(key=key).id)

    def test_installs_with_its_ledger_and_keeps_the_medicine_facts(self):
        self.assertTrue(RuntimeProvision.objects.get(instance=self.instance).completed_at)
        self.assertEqual(QuantityLedgerBinding.objects.filter(instance=self.instance).count(), 1)
        values = {
            "name": "Atrest 25mg Tablet 10'S",
            "generic_name": "Tetrabenazine 25 mg",
            "pack": "10 Tablet(s) in a Strip",
            "manufacturer": "Centaur Pharmaceuticals Pvt Ltd",
            "country_of_origin": "India",
            "prescription_required": True,
            "storage_location": "Shelf B3",
            "reference_price": "335.68",
            "reference_currency": "INR",
            "list_price": "120.00",
            "image_links": "https://example.com/a.jpg, https://example.com/b.jpg",
        }
        created = self.client.post(
            f"/api/v1/app-models/{self.model('part')}/records/",
            {self.field("part", k): v for k, v in values.items()},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        record = self.client.get(
            f"/api/v1/app-models/{self.model('part')}/records/{created.data['id']}/"
        ).data
        self.assertEqual(record[self.field("part", "generic_name")], "Tetrabenazine 25 mg")
        self.assertIs(record[self.field("part", "prescription_required")], True)
        self.assertEqual(record[self.field("part", "storage_location")], "Shelf B3")

    def test_a_medicine_and_its_item_number_import_together_or_not_at_all(self):
        part, number = self.model("part"), self.model("part_number")
        ops = [
            {
                "op": "create",
                "model": part,
                "ref": "m0",
                "data": {self.field("part", "name"): "Capnea Injection 1ml"},
            },
            {
                "op": "create",
                "model": number,
                "data": {
                    self.field("part_number", "number"): "NM-349693",
                    self.field("part_number", "part_number_part"): {"$ref": "m0"},
                },
            },
        ]
        url = f"/api/v1/app-instances/{self.instance.id}/transactions/"
        self.assertEqual(self.client.post(url, {"operations": ops}, format="json").status_code, 201)
        # The same item number again: the whole batch is refused, so no second medicine is left behind.
        again = self.client.post(url, {"operations": ops}, format="json")
        self.assertEqual(again.status_code, 400, again.data)
        names = self.client.get(f"/api/v1/app-models/{part}/records/").data
        self.assertEqual(names["count"], 1)

    def test_it_still_refuses_to_sell_stock_it_does_not_have(self):
        part = self.client.post(
            f"/api/v1/app-models/{self.model('part')}/records/",
            {self.field("part", "name"): "Paracetamol"},
            format="json",
        ).data["id"]
        warehouse = self.client.post(
            f"/api/v1/app-models/{self.model('warehouse')}/records/",
            {self.field("warehouse", "name"): "Main", self.field("warehouse", "code"): "MAIN"},
            format="json",
        ).data["id"]
        movement = self.client.post(
            f"/api/v1/app-models/{self.model('stock_movement')}/records/",
            {
                self.field("stock_movement", "quantity_delta"): -1,
                self.field("stock_movement", "movement_type"): "sale",
                self.field("stock_movement", "stock_movement_part"): part,
                self.field("stock_movement", "stock_movement_warehouse"): warehouse,
            },
            format="json",
        )
        self.assertNotEqual(movement.status_code, 201, movement.data)
