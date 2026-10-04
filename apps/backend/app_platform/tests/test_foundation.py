import copy
import json
import uuid
from datetime import timedelta

from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from accounts.models import User
from app_platform import instances, templates
from app_platform.definitions import validate_definition
from app_platform.models import (
    AppInstance,
    AppTemplate,
    AppTemplateVersion,
    FieldDefinition,
    RelationshipDefinition,
)
from audit.models import AuditEvent
from organizations.models import Membership
from organizations.services import create_organization
from permissions.services import grant_resource_permission
from workspaces.models import Project, Workspace


def sample():
    source, target = str(uuid.uuid4()), str(uuid.uuid4())
    return {
        "schema_version": 1,
        "models": [
            {
                "id": source,
                "key": "item",
                "label": "Item",
                "fields": [
                    {"key": "name", "label": "Name", "data_type": "text"},
                    {"key": "price", "label": "Price", "data_type": "decimal"},
                ],
            },
            {"id": target, "key": "group", "label": "Group", "fields": []},
        ],
        "relationships": [
            {
                "key": "group",
                "label": "Group",
                "source_model": source,
                "target_model": target,
            }
        ],
    }


def project_for(actor, org):
    workspace = Workspace.objects.create(organization=org, name="Workspace", created_by=actor)
    return Project.objects.create(workspace=workspace, name="Project", created_by=actor)


class FoundationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_permissions", verbosity=0)
        cls.owner = User.objects.create_user(email="app-owner@example.com", password="test-password")
        cls.other = User.objects.create_user(email="app-other@example.com", password="test-password")
        cls.org = create_organization(name="App Org", created_by=cls.owner)
        cls.other_org = create_organization(name="Other App Org", created_by=cls.other)
        cls.project = project_for(cls.owner, cls.org)
        cls.other_project = project_for(cls.other, cls.other_org)
        cls.template = templates.create_template(cls.owner, cls.org, {"label": "Example", "draft": sample()})
        cls.version = templates.publish_template(cls.owner, cls.template)
        cls.instance = instances.install(
            cls.owner,
            cls.project,
            {
                "template_version": str(cls.version.id),
                "label": "My application",
            },
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.owner)

    def grant(self, actor, code, obj, kind="app_instance", expires_at=None):
        return grant_resource_permission(
            user=actor,
            permission_code=code,
            organization_id=self.org.id,
            resource_type=kind,
            resource_id=obj.id,
            granted_by=self.owner,
            expires_at=expires_at,
        )

    def member(self):
        user = User.objects.create_user(email="member@example.com", password="test-password")
        Membership.objects.create(user=user, organization=self.org, status="active")
        return user

    def test_independent_installations_and_source_lineage(self):
        second = instances.install(
            self.owner,
            self.project,
            {
                "template_version": str(self.version.id),
                "label": "Second",
            },
        )
        first_model = self.instance.models.get(key="item")
        second_model = second.models.get(key="item")
        self.assertNotEqual(first_model.id, second_model.id)
        self.assertEqual(first_model.source_definition_id, second_model.source_definition_id)
        original = copy.deepcopy(self.version.definition)
        instances.update_definition(self.owner, first_model, {"label": "Renamed"})
        instances.add_field(self.owner, first_model, {"key": "sku", "label": "SKU", "data_type": "text"})
        self.version.refresh_from_db()
        self.assertEqual(self.version.definition, original)
        self.assertFalse(second_model.fields.filter(key="sku").exists())

    def test_rename_preserves_relationship_identity_and_reference(self):
        relation = self.instance.relationships.get()
        original_id, target_id = relation.id, relation.target_model_id
        instances.update_definition(self.owner, relation.target_model, {"label": "Category"})
        relation = instances.update_definition(self.owner, relation, {"label": "Category reference"})
        self.assertEqual((relation.id, relation.target_model_id), (original_id, target_id))

    def test_publishing_new_version_does_not_change_existing_installation(self):
        draft = copy.deepcopy(self.version.definition)
        draft["models"][0]["label"] = "New Item"
        templates.update_template(self.owner, self.template, {"draft": draft})
        second = templates.publish_template(self.owner, self.template)
        self.assertEqual(second.number, 2)
        self.assertEqual(second.definition["models"][0]["id"], self.version.definition["models"][0]["id"])
        self.assertEqual(self.instance.models.get(key="item").label, "Item")
        self.instance.refresh_from_db()
        self.assertEqual(self.instance.source_version_id, self.version.id)

    def test_version_database_update_and_delete_are_rejected(self):
        unused = templates.publish_template(self.owner, self.template)
        for operation in ("update", "delete"):
            with self.subTest(operation=operation), self.assertRaises(IntegrityError), transaction.atomic():
                with connection.cursor() as cursor:
                    if operation == "update":
                        cursor.execute(
                            "UPDATE app_platform_apptemplateversion SET number=99 WHERE id=%s", [unused.id]
                        )
                    else:
                        cursor.execute("DELETE FROM app_platform_apptemplateversion WHERE id=%s", [unused.id])

    def test_version_orm_mutation_and_api_mutation_are_rejected(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            AppTemplateVersion.objects.filter(pk=self.version.pk).update(definition={})
        self.assertEqual(
            self.client.patch(
                f"/api/v1/app-template-versions/{self.version.id}/", {}, format="json"
            ).status_code,
            405,
        )

    def test_keys_ownership_and_source_identity_are_database_immutable(self):
        model = self.instance.models.first()
        cases = [
            (AppTemplate.objects.filter(pk=self.template.pk), {"organization_id": self.other_org.id}),
            (AppInstance.objects.filter(pk=self.instance.pk), {"project_id": self.other_project.id}),
            (type(model).objects.filter(pk=model.pk), {"key": "changed"}),
            (model.fields.all(), {"source_definition_id": uuid.uuid4()}),
        ]
        # Pick the model with fields, independently of UUID ordering.
        cases[-1] = (
            self.instance.models.get(key="item").fields.all(),
            {"source_definition_id": uuid.uuid4()},
        )
        for queryset, updates in cases:
            with self.subTest(updates=updates), self.assertRaises(IntegrityError), transaction.atomic():
                queryset.update(**updates)

    def test_instance_database_rejects_cross_org_project(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            AppInstance.objects.create(
                organization=self.org,
                project=self.other_project,
                source_version=self.version,
                label="Bad",
                created_by=self.owner,
            )

    def test_relationship_boundaries_in_service_and_database(self):
        second = instances.install(
            self.owner, self.project, {"template_version": str(self.version.id), "label": "Second"}
        )
        source, target = self.instance.models.first(), second.models.first()
        with self.assertRaises(ValidationError):
            instances.add_relationship(
                self.owner,
                self.instance,
                {
                    "key": "bad",
                    "label": "Bad",
                    "source_model": str(source.id),
                    "target_model": str(target.id),
                },
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            RelationshipDefinition.objects.create(
                instance=self.instance,
                source_model=source,
                target_model=target,
                key="bad",
                label="Bad",
            )

    def test_self_relationship_and_explicit_set_null(self):
        model = self.instance.models.first()
        relation = instances.add_relationship(
            self.owner,
            self.instance,
            {
                "key": "parent",
                "label": "Parent",
                "source_model": str(model.id),
                "target_model": str(model.id),
                "deletion_policy": "set_null",
            },
        )
        self.assertEqual(relation.source_model_id, relation.target_model_id)
        self.assertEqual(relation.deletion_policy, "set_null")

    def test_invalid_identifiers_and_types_rejected_server_side(self):
        for key in ("id", "a;DROP TABLE x", "a\n", "UPPER", "a" * 64, " space", "a.b"):
            with self.subTest(key=key), self.assertRaises(ValidationError):
                instances.add_model(self.owner, self.instance, {"key": key, "label": "Bad"})
        model = self.instance.models.get(key="item")
        with self.assertRaises(ValidationError):
            instances.add_field(self.owner, model, {"key": "code", "label": "Code", "data_type": "python"})

    def test_draft_rejects_duplicates_external_references_unknown_properties_and_limits(self):
        base = self.version.definition
        duplicate = copy.deepcopy(base)
        duplicate["models"].append(copy.deepcopy(duplicate["models"][0]))
        foreign = copy.deepcopy(base)
        foreign["relationships"][0]["target_model"] = str(uuid.uuid4())
        extra = copy.deepcopy(base)
        extra["execute"] = "not allowed"
        many = {"schema_version": 1, "models": [base["models"][0]] * 101, "relationships": []}
        for value in (
            duplicate,
            foreign,
            extra,
            many,
            {"schema_version": 2, "models": [], "relationships": []},
        ):
            with self.subTest(value=str(value)[:80]), self.assertRaises(ValidationError):
                validate_definition(value)

    def test_duplicate_key_is_validation_error_and_database_constraint(self):
        with self.assertRaises(ValidationError):
            instances.add_model(self.owner, self.instance, {"key": "item", "label": "Duplicate"})
        model = self.instance.models.get(key="item")
        with self.assertRaises(IntegrityError), transaction.atomic():
            FieldDefinition.objects.create(model=model, key="name", label="Duplicate", data_type="text")

    def test_archive_stops_schema_edits_and_template_install_publish(self):
        instances.update_instance(self.owner, self.instance, {"archived": True})
        with self.assertRaises(ValidationError):
            instances.add_model(self.owner, self.instance, {"key": "extra", "label": "Extra"})
        templates.update_template(self.owner, self.template, {"archived": True})
        with self.assertRaises(ValidationError):
            templates.publish_template(self.owner, self.template)
        with self.assertRaises(ValidationError):
            instances.install(
                self.owner, self.project, {"template_version": str(self.version.id), "label": "Bad"}
            )

    def test_mass_assignment_rejected(self):
        model = self.instance.models.get(key="item")
        for url, data in (
            (f"app-instances/{self.instance.id}/", {"organization": str(self.other_org.id)}),
            (f"app-templates/{self.template.id}/", {"created_by": str(self.other.id)}),
            (f"app-models/{model.id}/", {"id": str(uuid.uuid4())}),
            (f"app-fields/{model.fields.first().id}/", {"data_type": "integer"}),
        ):
            self.assertEqual(self.client.patch(f"/api/v1/{url}", data, format="json").status_code, 400)

    def test_every_resource_endpoint_denies_foreign_organization(self):
        model = self.instance.models.get(key="item")
        paths = [
            f"organizations/{self.org.id}/app-templates/",
            f"app-templates/{self.template.id}/",
            f"app-templates/{self.template.id}/versions/",
            f"app-template-versions/{self.version.id}/",
            f"projects/{self.project.id}/app-instances/",
            f"app-instances/{self.instance.id}/",
            f"app-instances/{self.instance.id}/models/",
            f"app-models/{model.id}/",
            f"app-models/{model.id}/fields/",
            f"app-fields/{model.fields.first().id}/",
            f"app-instances/{self.instance.id}/relationships/",
            f"app-relationships/{self.instance.relationships.first().id}/",
        ]
        self.client.force_authenticate(self.other)
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(f"/api/v1/{path}").status_code, 404)
        for path in paths:
            if path.startswith("app-template-versions/"):
                continue
            method = (
                self.client.post
                if path.endswith(
                    ("templates/", "versions/", "instances/", "models/", "fields/", "relationships/")
                )
                else self.client.patch
            )
            with self.subTest(write=path):
                self.assertEqual(method(f"/api/v1/{path}", {}, format="json").status_code, 404)

    def test_membership_alone_cannot_read_write_or_publish(self):
        member = self.member()
        self.client.force_authenticate(member)
        for path in (f"app-templates/{self.template.id}/", f"app-instances/{self.instance.id}/"):
            self.assertEqual(self.client.get(f"/api/v1/{path}").status_code, 403)
            self.assertEqual(
                self.client.patch(f"/api/v1/{path}", {"label": "Bad"}, format="json").status_code, 403
            )
        self.assertEqual(
            self.client.post(
                f"/api/v1/app-templates/{self.template.id}/versions/", {}, format="json"
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(f"/api/v1/organizations/{self.org.id}/app-templates/").data["count"], 0
        )
        with self.assertRaises(PermissionDenied):
            instances.add_model(member, self.instance, {"key": "extra", "label": "Extra"})

    def test_exact_resource_grant_revocation_and_pagination(self):
        member = self.member()
        grant = self.grant(member, "app_instance.read", self.instance)
        self.client.force_authenticate(member)
        response = self.client.get(f"/api/v1/projects/{self.project.id}/app-instances/?limit=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(str(response.data["results"][0]["id"]), str(self.instance.id))
        self.assertEqual(
            self.client.get(f"/api/v1/app-instances/{self.instance.id}/models/?limit=1").data["count"], 2
        )
        grant.delete()
        self.assertEqual(self.client.get(f"/api/v1/app-instances/{self.instance.id}/").status_code, 403)

    def test_expired_grant_and_suspended_membership_do_not_authorize(self):
        member = self.member()
        grant = self.grant(
            member, "app_instance.read", self.instance, expires_at=timezone.now() - timedelta(seconds=1)
        )
        self.client.force_authenticate(member)
        self.assertEqual(self.client.get(f"/api/v1/app-instances/{self.instance.id}/").status_code, 403)
        grant.expires_at = None
        grant.save()
        Membership.objects.filter(user=member).update(status="suspended")
        self.assertEqual(self.client.get(f"/api/v1/app-instances/{self.instance.id}/").status_code, 404)

    def test_schema_grant_does_not_grant_install_or_publish(self):
        member = self.member()
        self.grant(member, "app_instance.schema.manage", self.instance)
        instances.add_model(member, self.instance, {"key": "extra", "label": "Extra"})
        with self.assertRaises(PermissionDenied):
            instances.install(
                member, self.project, {"template_version": str(self.version.id), "label": "Bad"}
            )
        with self.assertRaises(PermissionDenied):
            templates.publish_template(member, self.template)

    def test_same_actor_cannot_install_across_two_member_organizations(self):
        Membership.objects.create(user=self.owner, organization=self.other_org, status="active")
        from permissions.services import assign_role

        assign_role(user=self.owner, role_slug="organization-administrator", organization=self.other_org)
        with self.assertRaises(ValidationError):
            instances.install(
                self.owner, self.other_project, {"template_version": str(self.version.id), "label": "Bad"}
            )

    def test_unauthenticated_principal_denied(self):
        self.client.force_authenticate(None)
        self.assertIn(self.client.get(f"/api/v1/app-instances/{self.instance.id}/").status_code, (401, 403))

    def _service_account_user(self):
        from applications.models import Application, ServiceAccount

        service_user = self.member()
        application = Application.objects.create(organization=self.org, owner=self.owner, name="Integration")
        ServiceAccount.objects.create(application=application, identity_user=service_user)
        return service_user

    def test_service_account_without_a_grant_is_denied_even_on_an_opted_in_endpoint(self):
        """Post-Phase-3 Integration Enablement: InstanceDetail.get opts
        into bearer-token reachability (FoundationView.
        service_account_methods), but reachability grants nothing by
        itself -- deny-by-default still applies identically to a human
        session with no role/grant."""
        service_user = self._service_account_user()
        self.client.force_authenticate(service_user)
        self.assertEqual(self.client.get(f"/api/v1/app-instances/{self.instance.id}/").status_code, 403)

    def test_service_account_with_a_resource_grant_can_read_via_an_opted_in_endpoint(self):
        service_user = self._service_account_user()
        self.grant(service_user, "app_instance.read", self.instance)
        self.client.force_authenticate(service_user)
        response = self.client.get(f"/api/v1/app-instances/{self.instance.id}/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["id"], str(self.instance.id))

    def test_service_account_cannot_reach_a_method_not_opted_in_even_with_a_grant(self):
        """Even org-wide app_instance.manage (which would let a human
        PATCH this instance) doesn't help a bearer-token client here --
        InstanceDetail.patch was deliberately never added to
        service_account_methods (instance rename/archive stays
        administration, human-session-only in this first slice)."""
        service_user = self._service_account_user()
        self.grant(service_user, "app_instance.manage", self.instance)
        self.client.force_authenticate(service_user)
        response = self.client.patch(
            f"/api/v1/app-instances/{self.instance.id}/", {"label": "Hijacked"}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_service_account_cannot_install_a_new_instance_or_reach_template_administration(self):
        """No no-service_account_methods override on InstanceList/
        TemplateList/TemplateDetail/VersionList/VersionDetail -- template
        and instance-creation administration stays fully human-only
        regardless of any grant the service account holds."""
        service_user = self._service_account_user()
        self.grant(service_user, "app_template.manage", self.template, kind="app_template")
        self.grant(service_user, "app_instance.manage", self.instance)
        self.client.force_authenticate(service_user)
        install = self.client.post(
            f"/api/v1/projects/{self.project.id}/app-instances/",
            {"template_version": str(self.version.id), "label": "Sneaky"},
            format="json",
        )
        self.assertEqual(install.status_code, 403)
        template_read = self.client.get(f"/api/v1/app-templates/{self.template.id}/")
        self.assertEqual(template_read.status_code, 403)

    def test_audit_contains_identity_not_definition_payload_and_rolls_back(self):
        self.assertTrue(
            AuditEvent.objects.filter(
                action="app_template.publish", resource_id=str(self.template.id)
            ).exists()
        )
        self.assertTrue(
            AuditEvent.objects.filter(
                action="app_instance.install", resource_id=str(self.instance.id)
            ).exists()
        )
        instances.update_instance(self.owner, self.instance, {"archived": True})
        event = AuditEvent.objects.get(action="app_instance.archive", resource_id=str(self.instance.id))
        self.assertNotIn("models", json.dumps(event.context))
        from unittest.mock import patch

        before = AppTemplate.objects.count()
        with patch("app_platform.templates.event", side_effect=RuntimeError("audit failed")):
            with self.assertRaises(RuntimeError):
                templates.create_template(self.owner, self.org, {"label": "Rollback"})
        self.assertEqual(AppTemplate.objects.count(), before)

    def test_full_api_foundation_round_trip(self):
        response = self.client.post(
            f"/api/v1/organizations/{self.org.id}/app-templates/",
            {"label": "API", "draft": sample()},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        template_id = response.data["id"]
        version = self.client.post(f"/api/v1/app-templates/{template_id}/versions/", {}, format="json")
        self.assertEqual(version.status_code, 201, version.data)
        installed = self.client.post(
            f"/api/v1/projects/{self.project.id}/app-instances/",
            {"label": "API app", "template_version": version.data["id"]},
            format="json",
        )
        self.assertEqual(installed.status_code, 201, installed.data)
        rows = self.client.get(f"/api/v1/app-instances/{installed.data['id']}/models/")
        self.assertEqual(rows.data["count"], 2)

    def test_schema_api_create_inspect_and_patch(self):
        base = f"/api/v1/app-instances/{self.instance.id}"
        response = self.client.post(base + "/models/", {"key": "asset", "label": "Asset"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        model_id = response.data["id"]
        field = self.client.post(
            f"/api/v1/app-models/{model_id}/fields/",
            {"key": "enabled", "label": "Enabled", "data_type": "boolean"},
            format="json",
        )
        self.assertEqual(field.status_code, 201, field.data)
        field_path = f"/api/v1/app-fields/{field.data['id']}/"
        updated = self.client.patch(field_path, {"label": "Active", "required": True}, format="json")
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertTrue(self.client.get(field_path).data["required"])
        relation = self.client.post(
            base + "/relationships/",
            {
                "key": "parent",
                "label": "Parent",
                "source_model": model_id,
                "target_model": model_id,
            },
            format="json",
        )
        self.assertEqual(relation.status_code, 201, relation.data)
        path = f"/api/v1/app-relationships/{relation.data['id']}/"
        self.assertEqual(
            self.client.patch(path, {"deletion_policy": "set_null"}, format="json").status_code, 200
        )
        self.assertEqual(self.client.get(path).data["deletion_policy"], "set_null")
        self.assertTrue(AuditEvent.objects.filter(action="app_instance.fielddefinition.update").exists())
        self.assertTrue(
            AuditEvent.objects.filter(action="app_instance.relationshipdefinition.update").exists()
        )

    def test_install_audit_failure_rolls_back_all_copied_metadata(self):
        from unittest.mock import patch

        before = AppInstance.objects.count()
        fields_before = FieldDefinition.objects.count()
        with patch("app_platform.instances.event", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                instances.install(
                    self.owner,
                    self.project,
                    {
                        "label": "Rollback",
                        "template_version": str(self.version.id),
                    },
                )
        self.assertEqual(AppInstance.objects.count(), before)
        self.assertEqual(FieldDefinition.objects.count(), fields_before)

    def test_template_resource_grant_cannot_see_other_templates_or_publish(self):
        member = self.member()
        self.grant(member, "app_template.read", self.template, kind="app_template")
        hidden = templates.create_template(self.owner, self.org, {"label": "Hidden"})
        self.client.force_authenticate(member)
        response = self.client.get(f"/api/v1/organizations/{self.org.id}/app-templates/")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            self.client.get(f"/api/v1/app-template-versions/{self.version.id}/").status_code, 200
        )
        self.assertEqual(self.client.get(f"/api/v1/app-templates/{hidden.id}/").status_code, 403)
        self.assertEqual(
            self.client.post(
                f"/api/v1/app-templates/{self.template.id}/versions/", {}, format="json"
            ).status_code,
            403,
        )

    def test_model_deletion_is_protected_and_destructive_api_is_absent(self):
        from django.db.models.deletion import ProtectedError

        relation = self.instance.relationships.get()
        with self.assertRaises(ProtectedError):
            relation.target_model.delete()
        with self.assertRaises(ProtectedError):
            self.template.delete()
        self.assertEqual(self.client.delete(f"/api/v1/app-instances/{self.instance.id}/").status_code, 405)
