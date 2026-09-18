"""Phase 8 -- HR reference application
(docs/implementation/APP_PLATFORM_ROADMAP.md,
docs/implementation/APP_PLATFORM_PHASE8.md). Same bar as Phase 4's Spare
Parts template test suite: draft validity, install-time metadata, real
Postgres schema on provisioning (composite constraint mixing a field and
a relationship, self-referencing manager relationship, `org_unit_
reference` field), and a realistic workflow through the real record API.

Cross-org isolation is not re-tested here for the same reason Phase 4's
own suite gives: this template introduces no new endpoint or resource
type, only definitions installed through the existing, already-isolation-
tested `app_platform` pipeline."""

from django.core.management import call_command
from django.db import connections
from django.test import TestCase, TransactionTestCase
from psycopg import sql
from rest_framework.test import APIClient

from accounts.models import User
from app_platform import instances, provisioning, templates
from app_platform.definitions import validate_definition
from app_platform.reference_templates import hr_reference_definition
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for
from databases.models import DBIndex
from organizations.services import create_organization


class DraftValidationTests(TestCase):
    def test_the_draft_validates_cleanly(self):
        definition = validate_definition(hr_reference_definition())
        self.assertEqual(len(definition["models"]), 9)
        self.assertEqual(len(definition["relationships"]), 10)

    def test_payroll_record_has_a_mixed_composite_constraint(self):
        definition = validate_definition(hr_reference_definition())
        [payroll_record] = [m for m in definition["models"] if m["key"] == "payroll_record"]
        [constraint] = payroll_record["constraints"]
        self.assertEqual(len(constraint["field_ids"]), 1)
        self.assertEqual(len(constraint["relationship_ids"]), 1)


class InstallTests(TestCase):
    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.owner = User.objects.create_user(email="hr-install@example.com")
        self.org = create_organization(name="HR Install Org", created_by=self.owner)
        self.project = project_for(self.owner, self.org)

    def _install(self):
        template = templates.create_template(
            self.owner, self.org, {"label": "HR", "draft": hr_reference_definition()}
        )
        version = templates.publish_template(self.owner, template)
        return instances.install(
            self.owner, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )

    def test_install_creates_every_model(self):
        instance = self._install()
        keys = set(instance.models.values_list("key", flat=True))
        self.assertEqual(
            keys,
            {
                "department", "position", "employee", "leave_type", "leave_request",
                "timesheet", "payroll_record", "performance_review", "onboarding_task",
            },
        )

    def test_employee_manager_is_self_referencing(self):
        instance = self._install()
        employee = instance.models.get(key="employee")
        manager = employee.outgoing.get(key="manager")
        self.assertEqual(manager.source_model_id, employee.id)
        self.assertEqual(manager.target_model_id, employee.id)
        self.assertEqual(manager.deletion_policy, "set_null")

    def test_employee_has_org_unit_reference_field(self):
        instance = self._install()
        employee = instance.models.get(key="employee")
        field = employee.fields.get(key="org_unit")
        self.assertEqual(field.data_type, "org_unit_reference")


class ProvisioningAndWorkflowTests(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="hr-workflow@example.com")
        self.org = create_organization(name="HR Workflow Org", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        template = templates.create_template(
            self.actor, self.org, {"label": "HR", "draft": hr_reference_definition()}
        )
        version = templates.publish_template(self.actor, template)
        self.instance = instances.install(
            self.actor, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )
        self.models = {m.key: m for m in self.instance.models.all()}
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

    def _records_url(self, model_key):
        return f"/api/v1/app-models/{self.models[model_key].id}/records/"

    def _field(self, model_key, field_key):
        return self.models[model_key].fields.get(key=field_key)

    def _relation(self, model_key, relation_key):
        return self.models[model_key].outgoing.get(key=relation_key)

    def _create(self, model_key, **field_values):
        model = self.models[model_key]
        payload = {}
        for key, value in field_values.items():
            field = model.fields.filter(key=key).first()
            definition_id = field.id if field is not None else model.outgoing.get(key=key).id
            payload[str(definition_id)] = value
        response = self.client.post(self._records_url(model_key), payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def test_payroll_constraint_is_real_in_the_provisioned_schema(self):
        constraint = self.models["payroll_record"].constraints.get(key="employee_pay_period_unique")
        index_id = self.receipt.bindings["constraints"][str(constraint.id)]
        index = DBIndex.objects.get(pk=index_id)
        self.assertTrue(index.is_unique)

    def test_manager_self_reference_works_through_the_record_api(self):
        manager = self._create("employee", first_name="Sam", last_name="Lee", email="sam@example.com")
        report = self._create(
            "employee", first_name="Jo", last_name="Kim", email="jo@example.com", manager=manager["id"]
        )
        self.assertEqual(report[str(self._relation("employee", "manager").id)], manager["id"])

    def test_full_leave_timesheet_and_payroll_workflow(self):
        department = self._create("department", name="Engineering", code="ENG")
        position = self._create(
            "position", title="Software Engineer", code="SWE", position_department=department["id"]
        )
        employee = self._create(
            "employee", first_name="Riley", last_name="Chen", email="riley@example.com",
            employee_position=position["id"],
        )
        leave_type = self._create("leave_type", name="Vacation", code="VAC")
        self._create(
            "leave_request",
            leave_request_employee=employee["id"],
            leave_request_leave_type=leave_type["id"],
            start_date="2026-10-01",
            end_date="2026-10-05",
            status="pending",
        )
        self._create(
            "timesheet", timesheet_employee=employee["id"],
            period_start="2026-09-01", period_end="2026-09-15", total_hours="80", status="submitted",
        )
        self._create(
            "payroll_record", payroll_record_employee=employee["id"],
            pay_period_start="2026-09-01", pay_period_end="2026-09-15",
            gross_pay="4000.00", net_pay="3200.00", status="paid",
        )
        # One payroll record per (employee, pay_period_start) -- a
        # duplicate is genuinely rejected by the real composite constraint.
        duplicate = self.client.post(
            self._records_url("payroll_record"),
            {
                str(self._relation("payroll_record", "payroll_record_employee").id): employee["id"],
                str(self._field("payroll_record", "pay_period_start").id): "2026-09-01",
                str(self._field("payroll_record", "status").id): "pending",
            },
            format="json",
        )
        self.assertEqual(duplicate.status_code, 400, duplicate.data)

        review = self._create(
            "performance_review", performance_review_employee=employee["id"], reviewer=employee["id"],
            review_date="2026-09-16", rating=4,
        )
        self.assertEqual(review[str(self._relation("performance_review", "reviewer").id)], employee["id"])
