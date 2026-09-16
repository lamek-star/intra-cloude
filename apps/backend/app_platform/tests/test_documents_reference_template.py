"""Phase 8 -- Documents reference application
(docs/implementation/APP_PLATFORM_ROADMAP.md,
docs/implementation/APP_PLATFORM_PHASE8.md). Same bar as Phase 4's Spare
Parts template test suite: draft validity, install-time metadata, real
Postgres schema on provisioning (composite constraint mixing a field and
a relationship, self-referencing folder hierarchy, native many-to-many),
and a realistic workflow through the real record API.

Cross-org isolation is not re-tested here for the same reason Phase 4's
own suite gives: this template introduces no new endpoint or resource
type, only definitions installed through the existing, already-isolation-
tested `app_platform` pipeline. Attaching real file bytes to a Document
record reuses the existing generic per-record attachment API
(app_platform/tests/test_attachments.py already covers that path end to
end for every model) and is not re-proven here."""

from django.core.management import call_command
from django.db import connections
from django.test import TestCase, TransactionTestCase
from psycopg import sql
from rest_framework.test import APIClient

from accounts.models import User
from app_platform import instances, provisioning, templates
from app_platform.definitions import validate_definition
from app_platform.reference_templates import documents_reference_definition
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for
from databases.models import DBIndex
from organizations.services import create_organization


class DraftValidationTests(TestCase):
    def test_the_draft_validates_cleanly(self):
        definition = validate_definition(documents_reference_definition())
        self.assertEqual(len(definition["models"]), 6)
        self.assertEqual(len(definition["relationships"]), 6)

    def test_document_version_has_a_mixed_composite_constraint(self):
        definition = validate_definition(documents_reference_definition())
        [document_version] = [m for m in definition["models"] if m["key"] == "document_version"]
        [constraint] = document_version["constraints"]
        self.assertEqual(len(constraint["field_ids"]), 1)
        self.assertEqual(len(constraint["relationship_ids"]), 1)


class InstallTests(TestCase):
    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.owner = User.objects.create_user(email="documents-install@example.com")
        self.org = create_organization(name="Documents Install Org", created_by=self.owner)
        self.project = project_for(self.owner, self.org)

    def _install(self):
        template = templates.create_template(
            self.owner, self.org, {"label": "Documents", "draft": documents_reference_definition()}
        )
        version = templates.publish_template(self.owner, template)
        return instances.install(
            self.owner, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )

    def test_install_creates_every_model(self):
        instance = self._install()
        keys = set(instance.models.values_list("key", flat=True))
        self.assertEqual(
            keys, {"document_category", "document_folder", "document", "document_version", "tag", "document_review"}
        )

    def test_folder_parent_folder_is_self_referencing(self):
        instance = self._install()
        folder = instance.models.get(key="document_folder")
        parent = folder.outgoing.get(key="parent_folder")
        self.assertEqual(parent.source_model_id, folder.id)
        self.assertEqual(parent.target_model_id, folder.id)
        self.assertEqual(parent.deletion_policy, "set_null")

    def test_document_tags_is_many_to_many(self):
        instance = self._install()
        document = instance.models.get(key="document")
        relation = document.outgoing.get(key="tags")
        self.assertEqual(relation.kind, "many_to_many")


class ProvisioningAndWorkflowTests(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="documents-workflow@example.com")
        self.org = create_organization(name="Documents Workflow Org", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        template = templates.create_template(
            self.actor, self.org, {"label": "Documents", "draft": documents_reference_definition()}
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

    def test_document_version_constraint_is_real_in_the_provisioned_schema(self):
        constraint = self.models["document_version"].constraints.get(key="document_version_number_unique")
        index_id = self.receipt.bindings["constraints"][str(constraint.id)]
        index = DBIndex.objects.get(pk=index_id)
        self.assertTrue(index.is_unique)

    def test_folder_hierarchy_and_parent_deletion_orphans_children(self):
        parent = self._create("document_folder", name="Contracts")
        child = self._create("document_folder", name="2026", parent_folder=parent["id"])
        delete = self.client.delete(f"{self._records_url('document_folder')}{parent['id']}/")
        self.assertEqual(delete.status_code, 204, delete.data)
        refetched = self.client.get(f"{self._records_url('document_folder')}{child['id']}/")
        self.assertIsNone(refetched.data[str(self._relation("document_folder", "parent_folder").id)])

    def test_full_categorization_versioning_and_review_workflow(self):
        category = self._create("document_category", name="Policies", code="POL")
        folder = self._create("document_folder", name="HR Policies")
        document = self._create(
            "document", title="Leave Policy", document_category=category["id"], document_folder=folder["id"],
            status="draft", version=1,
        )
        self._create(
            "document_version", document_version_document=document["id"], version_number=1, notes="Initial draft"
        )
        # One version row per (document, version_number) -- a duplicate is
        # genuinely rejected by the real composite constraint.
        duplicate = self.client.post(
            self._records_url("document_version"),
            {
                str(self._relation("document_version", "document_version_document").id): document["id"],
                str(self._field("document_version", "version_number").id): 1,
            },
            format="json",
        )
        self.assertEqual(duplicate.status_code, 400, duplicate.data)

        review = self._create(
            "document_review", document_review_document=document["id"], reviewer_name="Legal", decision="approved"
        )
        self.assertEqual(review[str(self._relation("document_review", "document_review_document").id)], document["id"])

        tag = self._create("tag", name="HR")
        tags_relation = self._relation("document", "tags")
        linked = self.client.patch(
            f"{self._records_url('document')}{document['id']}/",
            {str(tags_relation.id): [tag["id"]]},
            format="json",
        )
        self.assertEqual(linked.status_code, 200, linked.data)
        self.assertEqual(linked.data[str(tags_relation.id)], [tag["id"]])
