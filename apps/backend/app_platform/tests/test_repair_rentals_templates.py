"""The Repair Shop and Rentals reference applications: each validates, installs and provisions, and a
realistic record flow works through the real record API with its constraints enforced by the provisioned
schema."""

from django.core.management import call_command
from django.db import connections
from django.test import TestCase, TransactionTestCase
from psycopg import sql
from rest_framework.test import APIClient

from accounts.models import User
from app_platform import instances, provisioning, templates
from app_platform.definitions import validate_definition
from app_platform.reference_templates import rentals_reference_definition, repair_shop_reference_definition
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for
from organizations.services import create_organization


class DraftTests(TestCase):
    def test_both_drafts_validate(self):
        repair = validate_definition(repair_shop_reference_definition())
        self.assertEqual((len(repair["models"]), len(repair["relationships"])), (6, 5))
        rentals = validate_definition(rentals_reference_definition())
        self.assertEqual((len(rentals["models"]), len(rentals["relationships"])), (5, 4))


class _Provisioned(TransactionTestCase):
    databases = {"default", "tenant"}
    builder = None
    label = ""

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email=f"{self.label.lower()}-flow@example.com")
        self.org = create_organization(name=f"{self.label} Org", created_by=self.actor)
        project = project_for(self.actor, self.org)
        template = templates.create_template(
            self.actor, self.org, {"label": self.label, "draft": type(self).builder()}
        )
        version = templates.publish_template(self.actor, template)
        self.instance = instances.install(
            self.actor, project, {"label": "Runtime", "template_version": str(version.id)}
        )
        self.models = {m.key: m for m in self.instance.models.all()}
        self.plan = plan_runtime(self.actor, self.instance)
        provisioning.reserve(self.actor, self.instance, self.plan["fingerprint"])
        provisioning.execute(self.instance.id, self.actor)
        self.client = APIClient()
        self.client.force_authenticate(self.actor)

    def tearDown(self):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.plan["schema_name"]))
            )
        super().tearDown()

    def payload(self, model_key, **values):
        model = self.models[model_key]
        out = {}
        for key, value in values.items():
            field = model.fields.filter(key=key).first()
            out[str(field.id if field is not None else model.outgoing.get(key=key).id)] = value
        return out

    def create(self, model_key, **values):
        r = self.client.post(
            f"/api/v1/app-models/{self.models[model_key].id}/records/",
            self.payload(model_key, **values),
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.data)
        return r.data


class RepairShopFlowTests(_Provisioned):
    builder = staticmethod(repair_shop_reference_definition)
    label = "Repair"

    def test_a_job_with_parts_labour_and_payment_and_unique_job_numbers(self):
        customer = self.create("customer", name="Selam", phone="0911223344")
        device = self.create("device", kind="Phone", brand="Tecno", device_customer=customer["id"])
        tech = self.create("technician", name="Dawit")
        job = self.create(
            "job",
            number="J-1001",
            fault="Screen broken",
            received_on="2026-11-12",
            estimate="1500.00",
            status="received",
            job_device=device["id"],
            job_technician=tech["id"],
        )
        self.create(
            "job_line",
            description="Screen",
            kind="part",
            quantity=1,
            unit_price="1200.00",
            job_line_job=job["id"],
        )
        self.create(
            "job_line",
            description="Fitting",
            kind="labour",
            quantity=1,
            unit_price="300.00",
            job_line_job=job["id"],
        )
        self.create("payment", paid_on="2026-11-13", amount="1500.00", method="cash", payment_job=job["id"])
        again = self.client.post(
            f"/api/v1/app-models/{self.models['job'].id}/records/",
            self.payload(
                "job",
                number="J-1001",
                fault="x",
                status="received",
                received_on="2026-11-12",
                job_device=device["id"],
            ),
            format="json",
        )
        self.assertEqual(again.status_code, 400, again.data)


class RentalsFlowTests(_Provisioned):
    builder = staticmethod(rentals_reference_definition)
    label = "Rentals"

    def test_a_booking_and_one_booking_per_item_starting_the_same_day(self):
        item = self.create("item", name="Drill", code="T-01", daily_price="150.00")
        customer = self.create("customer", name="Abel", phone="0922000111")
        self.create(
            "booking",
            starts_on="2026-11-14",
            ends_on="2026-11-16",
            status="booked",
            booking_item=item["id"],
            booking_customer=customer["id"],
            amount="450.00",
        )
        clash = self.client.post(
            f"/api/v1/app-models/{self.models['booking'].id}/records/",
            self.payload(
                "booking",
                starts_on="2026-11-14",
                ends_on="2026-11-15",
                status="booked",
                booking_item=item["id"],
                booking_customer=customer["id"],
            ),
            format="json",
        )
        self.assertEqual(clash.status_code, 400, clash.data)
