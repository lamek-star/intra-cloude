"""Phase 8 -- School reference application
(docs/implementation/APP_PLATFORM_ROADMAP.md,
docs/implementation/APP_PLATFORM_PHASE8.md). Same bar as Phase 4's Spare
Parts template test suite: draft validity, install-time metadata, real
Postgres schema on provisioning (composite constraint over two
relationships, native many-to-many), and a realistic workflow through the
real record API.

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
from app_platform.reference_templates import school_reference_definition
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for
from databases.models import DBIndex
from organizations.services import create_organization


class DraftValidationTests(TestCase):
    def test_the_draft_validates_cleanly(self):
        definition = validate_definition(school_reference_definition())
        self.assertEqual(len(definition["models"]), 11)
        self.assertEqual(len(definition["relationships"]), 10)

    def test_enrollment_has_a_relationship_only_composite_constraint(self):
        definition = validate_definition(school_reference_definition())
        [enrollment] = [m for m in definition["models"] if m["key"] == "enrollment"]
        [constraint] = enrollment["constraints"]
        self.assertEqual(constraint["field_ids"], [])
        self.assertEqual(len(constraint["relationship_ids"]), 2)


class InstallTests(TestCase):
    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.owner = User.objects.create_user(email="school-install@example.com")
        self.org = create_organization(name="School Install Org", created_by=self.owner)
        self.project = project_for(self.owner, self.org)

    def _install(self):
        template = templates.create_template(
            self.owner, self.org, {"label": "School", "draft": school_reference_definition()}
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
                "student", "guardian", "teacher", "department", "course", "term",
                "class_section", "enrollment", "attendance_record", "grade", "invoice",
            },
        )

    def test_enrollment_constraint_resolves_to_real_relationship_rows(self):
        instance = self._install()
        enrollment = instance.models.get(key="enrollment")
        constraint = enrollment.constraints.get(key="student_class_section_unique")
        self.assertEqual(constraint.fields.count(), 0)
        self.assertEqual(
            {r.target_model.key for r in constraint.relationships.all()},
            {"student", "class_section"},
        )

    def test_student_guardians_is_many_to_many(self):
        instance = self._install()
        student = instance.models.get(key="student")
        relation = student.outgoing.get(key="guardians")
        self.assertEqual(relation.kind, "many_to_many")
        self.assertEqual(relation.target_model.key, "guardian")


class ProvisioningAndWorkflowTests(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="school-workflow@example.com")
        self.org = create_organization(name="School Workflow Org", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        template = templates.create_template(
            self.actor, self.org, {"label": "School", "draft": school_reference_definition()}
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

    def test_enrollment_composite_constraint_is_real_in_the_provisioned_schema(self):
        constraint = self.models["enrollment"].constraints.get(key="student_class_section_unique")
        index_id = self.receipt.bindings["constraints"][str(constraint.id)]
        index = DBIndex.objects.get(pk=index_id)
        self.assertTrue(index.is_unique)

    def test_full_enrollment_attendance_and_grading_workflow(self):
        department = self._create("department", name="Mathematics", code="MATH")
        course = self._create("course", title="Algebra I", code="ALG1", course_department=department["id"], credits=3)
        term = self._create("term", name="Fall 2026")
        teacher = self._create("teacher", name="Ms. Rivera")
        class_section = self._create(
            "class_section",
            section_code="ALG1-A",
            class_section_course=course["id"],
            class_section_term=term["id"],
            class_section_teacher=teacher["id"],
            capacity=30,
        )
        student = self._create("student", name="Alex Doe")

        self._create(
            "enrollment",
            enrollment_student=student["id"],
            enrollment_class_section=class_section["id"],
            status="enrolled",
        )
        # One enrollment per (student, class_section) -- a duplicate is
        # genuinely rejected by the real composite constraint.
        duplicate = self.client.post(
            self._records_url("enrollment"),
            {
                str(self._relation("enrollment", "enrollment_student").id): student["id"],
                str(self._relation("enrollment", "enrollment_class_section").id): class_section["id"],
                str(self._field("enrollment", "status").id): "enrolled",
            },
            format="json",
        )
        self.assertEqual(duplicate.status_code, 400, duplicate.data)

        enrollment = self.client.get(self._records_url("enrollment")).data["results"][0]
        self._create("attendance_record", date="2026-09-16", present=True, attendance_enrollment=enrollment["id"])
        grade = self._create("grade", score="92.5", grade_letter="A", grade_enrollment=enrollment["id"])
        self.assertEqual(grade[str(self._field("grade", "grade_letter").id)], "A")

        invoice = self._create(
            "invoice", invoice_number="SCH-0001", amount_due="500.00", status="unpaid", invoice_student=student["id"]
        )
        self.assertEqual(invoice[str(self._field("invoice", "invoice_number").id)], "SCH-0001")

        guardian = self._create("guardian", name="Jamie Doe")
        guardians_relation = self._relation("student", "guardians")
        linked = self.client.patch(
            f"{self._records_url('student')}{student['id']}/",
            {str(guardians_relation.id): [guardian["id"]]},
            format="json",
        )
        self.assertEqual(linked.status_code, 200, linked.data)
        self.assertEqual(linked.data[str(guardians_relation.id)], [guardian["id"]])
