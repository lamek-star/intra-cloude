"""Phase 9 -- template versioning and upgrades
(docs/implementation/APP_PLATFORM_ROADMAP.md,
docs/implementation/APP_PLATFORM_PHASE9.md). Proves the three-way
comparison (source snapshot the instance was installed from, the
instance's own live configuration, and a newer published version) against
a real provisioned instance, through the real HTTP API, exactly the bar
every other App Platform feature test in this suite uses.

Cross-org isolation for the *instance* endpoint itself is not re-tested
here (test_foundation.py::test_every_resource_endpoint_denies_foreign_
organization already covers `get_owned` for `AppInstance`); this file's
own cross-org case is specific to Phase 9 -- naming a *version from
another organization's template* as the upgrade target."""

import copy
import uuid

from django.core.management import call_command
from django.db import connections
from django.test import TransactionTestCase
from psycopg import sql
from rest_framework.test import APIClient

from accounts.models import User
from app_platform import instances, provisioning, templates
from app_platform.reference_templates._helpers import _field, _model, _relationship
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for
from organizations.services import create_organization


def _draft_v1():
    item_id, group_id, tag_id = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    name_id, name_field = _field("name", "Name", "text", required=True)
    price_id, price_field = _field("price", "Price", "decimal")
    legacy_id, legacy_field = _field("legacy_note", "Legacy Note", "text")
    item = _model(
        item_id, "item", "Item",
        [(name_id, name_field), (price_id, price_field), (legacy_id, legacy_field)],
    )
    group = _model(group_id, "group", "Group", [])
    relationship = _relationship("group", "Group", item_id, group_id)
    ids = {
        "item": item_id, "group": group_id, "tag": tag_id,
        "name": name_id, "price": price_id, "legacy_note": legacy_id,
        "item_group": relationship["id"],
    }
    draft = {"schema_version": 1, "models": [item, group], "relationships": [relationship]}
    return draft, ids


def _draft_v2(v1_draft, ids):
    """Built by mutating a deep copy of v1's own already-id-filled draft,
    matching the architecture doc's own "authors must retain returned
    UUIDs to retain lineage" rule -- every id kept from v1 is a
    same-element edit; every new id is a genuinely new element."""
    draft = copy.deepcopy(v1_draft)
    item, group = draft["models"]
    assert item["key"] == "item" and group["key"] == "group"

    item["label"] = "Product"  # changed upstream -- will conflict with a local rename in tests below
    name_field = next(f for f in item["fields"] if f["id"] == ids["name"])
    name_field["required"] = False  # structural change to an EXISTING field -- never auto-applied
    item["fields"] = [f for f in item["fields"] if f["id"] != ids["legacy_note"]]  # removed upstream

    group["label"] = "Category"  # changed upstream, never touched locally -- safe to sync

    tag_name_id, tag_name_field = _field("name", "Name", "text", required=True)
    tag = _model(ids["tag"], "tag", "Tag", [(tag_name_id, tag_name_field)])
    draft["models"].append(tag)
    ids["tag_name"] = tag_name_id

    tag_ref = _relationship("tag_ref", "Tag", ids["item"], ids["tag"])
    draft["relationships"].append(tag_ref)
    ids["item_tag_ref"] = tag_ref["id"]

    item["constraints"] = [
        {
            "key": "price_tag_unique",
            "label": "Unique Price+Tag",
            "field_ids": [ids["price"]],
            "relationship_ids": [tag_ref["id"]],
        }
    ]
    return draft


class UpgradeTestsBase(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="upgrade-owner@example.com")
        self.org = create_organization(name="Upgrade Org", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        v1_draft, self.ids = _draft_v1()
        self.template = templates.create_template(
            self.actor, self.org, {"label": "Upgradeable", "draft": v1_draft}
        )
        self.v1 = templates.publish_template(self.actor, self.template)
        self.instance = instances.install(
            self.actor, self.project, {"label": "Runtime", "template_version": str(self.v1.id)}
        )
        self.plan = plan_runtime(self.actor, self.instance)
        provisioning.reserve(self.actor, self.instance, self.plan["fingerprint"])
        self.receipt = provisioning.execute(self.instance.id, self.actor)
        self.client = APIClient()
        self.client.force_authenticate(self.actor)

        # A customer-made local customization with NO template lineage at
        # all -- must survive every upgrade untouched and unreported.
        self.local_model = instances.add_model(self.actor, self.instance, {"key": "notes", "label": "Notes"})

        # A customer-made local RENAME of a template-sourced item -- sets
        # up the label_conflict case once v2 renames the same item too.
        item = self.instance.models.get(key="item")
        instances.update_definition(self.actor, item, {"label": "My Item"})

        v2_draft = _draft_v2(self.v1.definition, self.ids)
        templates.update_template(self.actor, self.template, {"draft": v2_draft})
        self.v2 = templates.publish_template(self.actor, self.template)

    def tearDown(self):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.plan["schema_name"]))
            )
        super().tearDown()

    def preview(self, version):
        return self.client.get(f"/api/v1/app-instances/{self.instance.id}/upgrade/{version.id}/")

    def apply(self, version):
        return self.client.post(
            f"/api/v1/app-instances/{self.instance.id}/upgrade/{version.id}/", {}, format="json"
        )


class PreviewTests(UpgradeTestsBase):
    def test_preview_never_mutates_anything(self):
        before = list(self.instance.models.values_list("key", flat=True))
        response = self.preview(self.v2)
        self.assertEqual(response.status_code, 200, response.data)
        after = list(self.instance.models.values_list("key", flat=True))
        self.assertEqual(before, after)
        self.instance.refresh_from_db()
        self.assertEqual(self.instance.source_version_id, self.v1.id)

    def test_new_model_and_field_are_categorized_as_additions(self):
        diff = self.preview(self.v2).data
        added_model_ids = {m["id"] for m in diff["models"]["add"]}
        self.assertIn(self.ids["tag"], added_model_ids)
        added_field_ids = {f["id"] for f in diff["fields"]["add"]}
        self.assertIn(self.ids["tag_name"], added_field_ids)
        added_relationship_ids = {r["id"] for r in diff["relationships"]["add"]}
        self.assertIn(self.ids["item_tag_ref"], added_relationship_ids)
        added_constraint_keys = {c["key"] for c in diff["constraints"]["add"]}
        self.assertIn("price_tag_unique", added_constraint_keys)

    def test_untouched_upstream_change_with_no_local_edit_is_a_label_sync(self):
        diff = self.preview(self.v2).data
        [entry] = [e for e in diff["models"]["label_sync"] if e["id"] == self.ids["group"]]
        self.assertEqual(entry["from"], "Group")
        self.assertEqual(entry["to"], "Category")

    def test_conflicting_local_and_upstream_label_change_is_manual_review(self):
        diff = self.preview(self.v2).data
        [entry] = [e for e in diff["models"]["manual_review"] if e["id"] == self.ids["item"]]
        self.assertEqual(entry["reason"], "label_conflict")
        self.assertEqual(entry["template_label"], "Product")
        self.assertEqual(entry["live_label"], "My Item")

    def test_structural_field_change_is_manual_review_never_an_addition_or_sync(self):
        diff = self.preview(self.v2).data
        [entry] = [e for e in diff["fields"]["manual_review"] if e["id"] == self.ids["name"]]
        self.assertEqual(entry["reason"], "structural_change_unsupported")
        self.assertEqual(entry["changed_fields"], ["required"])
        all_add_ids = {f["id"] for f in diff["fields"]["add"]}
        all_sync_ids = {f["id"] for f in diff["fields"]["label_sync"]}
        self.assertNotIn(self.ids["name"], all_add_ids)
        self.assertNotIn(self.ids["name"], all_sync_ids)

    def test_field_removed_upstream_is_manual_review(self):
        diff = self.preview(self.v2).data
        [entry] = [e for e in diff["fields"]["manual_review"] if e["id"] == self.ids["legacy_note"]]
        self.assertEqual(entry["reason"], "removed_upstream_unsupported")

    def test_local_only_customization_never_appears_in_the_diff(self):
        diff = self.preview(self.v2).data
        for kind in ("models", "fields", "relationships", "constraints"):
            all_ids = {
                entry.get("id")
                for bucket in diff[kind].values()
                for entry in bucket
            }
            self.assertNotIn(str(self.local_model.id), all_ids)

    def test_target_version_from_a_different_template_is_rejected(self):
        other_draft, _ = _draft_v1()
        other_template = templates.create_template(
            self.actor, self.org, {"label": "Other", "draft": other_draft}
        )
        other_version = templates.publish_template(self.actor, other_template)
        response = self.preview(other_version)
        self.assertEqual(response.status_code, 400, response.data)

    def test_target_version_from_a_foreign_organization_is_not_found(self):
        outsider = User.objects.create_user(email="upgrade-outsider@example.com")
        other_org = create_organization(name="Outsider Org", created_by=outsider)
        other_draft, _ = _draft_v1()
        other_template = templates.create_template(
            outsider, other_org, {"label": "Foreign", "draft": other_draft}
        )
        other_version = templates.publish_template(outsider, other_template)
        response = self.preview(other_version)
        self.assertEqual(response.status_code, 404, response.data)

    def test_target_version_not_newer_than_current_is_rejected(self):
        response = self.preview(self.v1)
        self.assertEqual(response.status_code, 400, response.data)


class ApplyTests(UpgradeTestsBase):
    def test_apply_records_a_receipt_without_touching_permanent_provenance(self):
        response = self.apply(self.v2)
        self.assertEqual(response.status_code, 201, response.data)
        self.instance.refresh_from_db()
        # instance.source_version is permanent install provenance,
        # immutable at the DB level (migration 0002's app_instance_identity
        # trigger) -- it never changes. upgrades.py tracks the actual
        # current baseline via the AppInstanceUpgrade trail instead (see
        # upgrades._base_version).
        self.assertEqual(self.instance.source_version_id, self.v1.id)
        self.assertEqual(response.data["from_version"], self.v1.id)
        self.assertEqual(response.data["to_version"], self.v2.id)

        history = self.client.get(f"/api/v1/app-instances/{self.instance.id}/upgrades/")
        self.assertEqual(history.status_code, 200, history.data)
        self.assertEqual(history.data["count"], 1)

    def test_new_model_field_relationship_and_constraint_are_really_created(self):
        self.apply(self.v2)
        tag = self.instance.models.get(source_definition_id=self.ids["tag"])
        self.assertEqual(tag.key, "tag")
        tag_name = tag.fields.get(source_definition_id=self.ids["tag_name"])
        self.assertEqual(tag_name.key, "name")
        relation = self.instance.relationships.get(source_definition_id=self.ids["item_tag_ref"])
        self.assertEqual(relation.target_model_id, tag.id)
        item = self.instance.models.get(source_definition_id=self.ids["item"])
        constraint = item.constraints.get(key="price_tag_unique")
        self.assertEqual(constraint.fields.count(), 1)
        self.assertEqual(constraint.relationships.count(), 1)

    def test_new_model_and_field_work_through_the_real_provisioned_record_api(self):
        self.apply(self.v2)
        tag = self.instance.models.get(source_definition_id=self.ids["tag"])
        tag_name = tag.fields.get(source_definition_id=self.ids["tag_name"])
        response = self.client.post(
            f"/api/v1/app-models/{tag.id}/records/", {str(tag_name.id): "Sale"}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data[str(tag_name.id)], "Sale")

    def test_new_constraint_genuinely_rejects_a_duplicate_through_the_real_api(self):
        self.apply(self.v2)
        item = self.instance.models.get(source_definition_id=self.ids["item"])
        tag = self.instance.models.get(source_definition_id=self.ids["tag"])
        tag_name = tag.fields.get(source_definition_id=self.ids["tag_name"])
        price = item.fields.get(source_definition_id=self.ids["price"])
        name = item.fields.get(source_definition_id=self.ids["name"])
        tag_ref = item.outgoing.get(source_definition_id=self.ids["item_tag_ref"])
        tag_record = self.client.post(
            f"/api/v1/app-models/{tag.id}/records/", {str(tag_name.id): "Clearance"}, format="json"
        ).data

        def _create_item(price_value):
            return self.client.post(
                f"/api/v1/app-models/{item.id}/records/",
                # `name` is still required -- v2's attempt to relax that
                # is an unapplied structural change (see
                # test_structural_change_and_removed_field_are_never_applied).
                {str(name.id): "Widget", str(price.id): price_value, str(tag_ref.id): tag_record["id"]},
                format="json",
            )

        first = _create_item("9.99")
        self.assertEqual(first.status_code, 201, first.data)
        duplicate = _create_item("9.99")
        self.assertEqual(duplicate.status_code, 400, duplicate.data)

    def test_label_sync_is_applied_and_conflict_is_left_alone(self):
        self.apply(self.v2)
        group = self.instance.models.get(source_definition_id=self.ids["group"])
        self.assertEqual(group.label, "Category")
        item = self.instance.models.get(source_definition_id=self.ids["item"])
        self.assertEqual(item.label, "My Item")  # the customer's local rename, never overwritten

    def test_structural_change_and_removed_field_are_never_applied(self):
        self.apply(self.v2)
        item = self.instance.models.get(source_definition_id=self.ids["item"])
        name = item.fields.get(source_definition_id=self.ids["name"])
        self.assertTrue(name.required)  # v2 said False; never applied
        self.assertTrue(item.fields.filter(source_definition_id=self.ids["legacy_note"]).exists())

    def test_local_customization_survives_an_upgrade_untouched(self):
        self.apply(self.v2)
        self.local_model.refresh_from_db()
        self.assertEqual(self.local_model.label, "Notes")
        self.assertIsNone(self.local_model.source_definition_id)

    def test_reapplying_the_same_version_is_rejected(self):
        first = self.apply(self.v2)
        self.assertEqual(first.status_code, 201, first.data)
        second = self.apply(self.v2)
        self.assertEqual(second.status_code, 400, second.data)

    def test_a_persisting_conflict_is_recomputed_fresh_against_the_next_version(self):
        self.apply(self.v2)
        v3_draft = copy.deepcopy(self.v2.definition)
        [item] = [m for m in v3_draft["models"] if m["id"] == self.ids["item"]]
        item["label"] = "Widget"
        templates.update_template(self.actor, self.template, {"draft": v3_draft})
        v3 = templates.publish_template(self.actor, self.template)

        diff = self.preview(v3).data
        [entry] = [e for e in diff["models"]["manual_review"] if e["id"] == self.ids["item"]]
        self.assertEqual(entry["reason"], "label_conflict")
        self.assertEqual(entry["template_label"], "Widget")
        self.assertEqual(entry["live_label"], "My Item")
