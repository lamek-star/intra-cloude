"""Composite (multi-field) uniqueness for App Platform models -- the
general capability docs/SPARE_PARTS_INTEGRATION_READINESS.md's "Inventory
(Part x Warehouse)" row tracked as PARTIAL, deliberately not closed by the
narrow, join-table-specific `databases.services.add_composite_unique_
constraint` many-to-many uses (app_platform/tests/test_many_to_many.py).

Covers: draft/template-level validation (definitions.py's ConstraintInput/
SnapshotConstraint), install-time metadata creation, fresh provisioning, a
real Postgres composite UNIQUE constraint enforcing it (create/update
conflicts, concurrency, NULL semantics), live additive schema evolution
against a populated instance (clean vs. duplicate data), idempotent
reprovisioning, label-rename/field-reorder stability, invalid field-
reference rejection, and tenant isolation. The underlying N-column
primitive itself (databases.services.add_field_set_unique_constraint) is
unit-tested independently in databases/tests/test_indexing.py; this file
proves the App Platform-level wiring end to end, mirroring test_field_
indexing.py's own structure for the existing single-field case."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from django.core.management import call_command
from django.db import close_old_connections, connections, transaction
from django.test import TestCase, TransactionTestCase
from psycopg import sql
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from accounts.models import User
from app_platform import definitions, instances, provisioning, schema_evolution, templates
from app_platform.models import ConstraintDefinition
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for, sample
from databases.models import DBIndex
from organizations.models import Membership
from organizations.services import create_organization
from permissions.services import assign_role, grant_resource_permission


def composite_sample():
    """A single-model draft with two scalar fields and a declared
    composite unique constraint over both, built with explicit field ids
    (rather than mutating sample()'s output after the fact) since a
    constraint's field_ids must reference ids already present in the same
    payload -- exactly how sample()'s own relationship already
    pre-generates its source/target model ids."""
    model_id = str(uuid.uuid4())
    name_id = str(uuid.uuid4())
    price_id = str(uuid.uuid4())
    return {
        "schema_version": 1,
        "models": [
            {
                "id": model_id,
                "key": "item",
                "label": "Item",
                "fields": [
                    {"id": name_id, "key": "name", "label": "Name", "data_type": "text"},
                    {"id": price_id, "key": "price", "label": "Price", "data_type": "decimal"},
                ],
                "constraints": [
                    {
                        "key": "name_price_unique",
                        "label": "Unique Name+Price",
                        "field_ids": [name_id, price_id],
                    }
                ],
            }
        ],
        "relationships": [],
    }


class DraftValidationTests(TestCase):
    """Pure metadata validation -- definitions.validate_definition, no
    tenant DB involved."""

    def test_a_valid_two_field_constraint_is_accepted(self):
        definition = definitions.validate_definition(composite_sample())
        [model] = definition["models"]
        [constraint] = model["constraints"]
        self.assertEqual(constraint["key"], "name_price_unique")
        self.assertEqual(len(constraint["field_ids"]), 2)

    def test_a_constraint_with_only_one_field_is_rejected(self):
        d = composite_sample()
        d["models"][0]["constraints"][0]["field_ids"] = [d["models"][0]["fields"][0]["id"]]
        with self.assertRaises(ValidationError):
            definitions.validate_definition(d)

    def test_a_repeated_field_id_in_one_constraint_is_rejected(self):
        d = composite_sample()
        name_id = d["models"][0]["fields"][0]["id"]
        d["models"][0]["constraints"][0]["field_ids"] = [name_id, name_id]
        with self.assertRaises(ValidationError):
            definitions.validate_definition(d)

    def test_a_constraint_field_from_a_different_model_is_rejected(self):
        d = composite_sample()
        other_model_id = str(uuid.uuid4())
        other_field_id = str(uuid.uuid4())
        d["models"].append(
            {
                "id": other_model_id,
                "key": "other",
                "label": "Other",
                "fields": [{"id": other_field_id, "key": "tag", "label": "Tag", "data_type": "text"}],
            }
        )
        d["models"][0]["constraints"][0]["field_ids"][1] = other_field_id
        with self.assertRaises(ValidationError):
            definitions.validate_definition(d)

    def test_a_constraint_field_that_does_not_exist_is_rejected(self):
        d = composite_sample()
        d["models"][0]["constraints"][0]["field_ids"][1] = str(uuid.uuid4())
        with self.assertRaises(ValidationError):
            definitions.validate_definition(d)

    def test_a_model_without_constraints_still_validates_unchanged(self):
        definition = definitions.validate_definition(sample())
        for model in definition["models"]:
            self.assertEqual(model["constraints"], [])


class InstallTests(TestCase):
    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.owner = User.objects.create_user(email="cx-install@example.com")
        self.org = create_organization(name="CX Install Org", created_by=self.owner)
        self.project = project_for(self.owner, self.org)

    def test_installing_a_template_with_a_constraint_creates_a_constraint_definition(self):
        draft = {"label": "App", "draft": composite_sample()}
        template = templates.create_template(self.owner, self.org, draft)
        version = templates.publish_template(self.owner, template)
        instance = instances.install(
            self.owner, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )
        item = instance.models.get(key="item")
        constraint = item.constraints.get(key="name_price_unique")
        self.assertEqual(constraint.label, "Unique Name+Price")
        self.assertEqual(
            {f.key for f in constraint.fields.all()},
            {"name", "price"},
        )


class ProvisioningTestBase(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="cx-provision@example.com")
        self.org = create_organization(name="CX Provision Org", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        self.client = APIClient()
        self.client.force_authenticate(self.actor)

    def _install(self, draft):
        template = templates.create_template(self.actor, self.org, {"label": "App", "draft": draft})
        version = templates.publish_template(self.actor, template)
        return instances.install(
            self.actor, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )

    def _provision(self, instance):
        plan = plan_runtime(self.actor, instance)
        provisioning.reserve(self.actor, instance, plan["fingerprint"])
        receipt = provisioning.execute(instance.id, self.actor)
        return plan, receipt

    def _drop_schema(self, plan):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(plan["schema_name"]))
            )

    def _create(self, model_id, name_field, price_field, name, price):
        return self.client.post(
            f"/api/v1/app-models/{model_id}/records/",
            {str(name_field.id): name, str(price_field.id): price},
            format="json",
        )


class FreshProvisioningTests(ProvisioningTestBase):
    def setUp(self):
        super().setUp()
        self.instance = self._install(composite_sample())
        self.item = self.instance.models.get(key="item")
        self.name_field = self.item.fields.get(key="name")
        self.price_field = self.item.fields.get(key="price")
        self.plan, self.receipt = self._provision(self.instance)

    def tearDown(self):
        self._drop_schema(self.plan)
        super().tearDown()

    def test_fresh_provisioning_creates_a_real_composite_unique_index(self):
        column_a = self.receipt.bindings["fields"][str(self.name_field.id)]
        column_b = self.receipt.bindings["fields"][str(self.price_field.id)]
        constraint = self.item.constraints.get(key="name_price_unique")
        index_id = self.receipt.bindings["constraints"][str(constraint.id)]
        index = DBIndex.objects.get(pk=index_id)
        self.assertTrue(index.is_unique)
        self.assertEqual(
            {str(c) for c in index.columns.values_list("id", flat=True)}, {column_a, column_b}
        )
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                "SELECT indexdef FROM pg_indexes WHERE schemaname = %s AND indexname = %s",
                [self.receipt.database.schema_name, index.name],
            )
            [indexdef] = cursor.fetchone()
        self.assertIn("UNIQUE", indexdef)

    def test_unique_combination_succeeds(self):
        resp = self._create(self.item.id, self.name_field, self.price_field, "Bolt", "1.00")
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_duplicate_combination_create_is_rejected(self):
        self._create(self.item.id, self.name_field, self.price_field, "Bolt", "1.00")
        dupe = self._create(self.item.id, self.name_field, self.price_field, "Bolt", "1.00")
        self.assertEqual(dupe.status_code, 400, dupe.data)
        self.assertIn("already exists", dupe.data["detail"])

    def test_same_a_different_b_succeeds(self):
        first = self._create(self.item.id, self.name_field, self.price_field, "Bolt", "1.00")
        second = self._create(self.item.id, self.name_field, self.price_field, "Bolt", "2.00")
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 201, second.data)

    def test_different_a_same_b_succeeds(self):
        first = self._create(self.item.id, self.name_field, self.price_field, "Bolt", "1.00")
        second = self._create(self.item.id, self.name_field, self.price_field, "Nut", "1.00")
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 201, second.data)

    def test_duplicate_update_is_rejected(self):
        self._create(self.item.id, self.name_field, self.price_field, "Bolt", "1.00")
        second = self._create(self.item.id, self.name_field, self.price_field, "Nut", "2.00")
        clash = self.client.patch(
            f"/api/v1/app-models/{self.item.id}/records/{second.data['id']}/",
            {str(self.name_field.id): "Bolt", str(self.price_field.id): "1.00"},
            format="json",
        )
        self.assertEqual(clash.status_code, 400, clash.data)
        self.assertIn("already exists", clash.data["detail"])

    def test_concurrent_duplicate_creation_the_database_constraint_is_the_real_gate(self):
        def create(_):
            close_old_connections()
            client = APIClient()
            client.force_authenticate(self.actor)
            try:
                return client.post(
                    f"/api/v1/app-models/{self.item.id}/records/",
                    {str(self.name_field.id): "Race", str(self.price_field.id): "9.00"},
                    format="json",
                )
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(create, [None, None]))

        statuses = sorted(r.status_code for r in responses)
        self.assertEqual(statuses, [201, 400])
        listing = self.client.get(f"/api/v1/app-models/{self.item.id}/records/")
        matches = [
            r
            for r in listing.data["results"]
            if r[str(self.name_field.id)] == "Race"
            and Decimal(str(r[str(self.price_field.id)])) == Decimal("9.00")
        ]
        self.assertEqual(len(matches), 1)

    def test_null_in_a_nullable_participating_field_is_not_treated_as_a_duplicate(self):
        """Documented, deliberate PostgreSQL semantics (see
        ConstraintDefinition's own docstring and databases.services.
        add_field_set_unique_constraint's): both fields here are
        `required=False`, so two records that both leave `price` blank
        (NULL) are not duplicates even though `name` matches, because
        Postgres never treats NULL as equal to another NULL."""
        first = self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/",
            {str(self.name_field.id): "NoPrice"},
            format="json",
        )
        second = self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/",
            {str(self.name_field.id): "NoPrice"},
            format="json",
        )
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 201, second.data)
        self.assertIsNone(first.data[str(self.price_field.id)])
        self.assertIsNone(second.data[str(self.price_field.id)])


class SingleFieldUniqueRemainsUnaffectedTests(ProvisioningTestBase):
    """A composite constraint on two OTHER fields coexists with an
    existing single-field unique field on the same model without either
    interfering with the other -- the two mechanisms are independent."""

    def setUp(self):
        super().setUp()
        draft = composite_sample()
        draft["models"][0]["fields"].append(
            {"key": "sku", "label": "SKU", "data_type": "text", "unique": True}
        )
        self.instance = self._install(draft)
        self.item = self.instance.models.get(key="item")
        self.name_field = self.item.fields.get(key="name")
        self.price_field = self.item.fields.get(key="price")
        self.sku_field = self.item.fields.get(key="sku")
        self.plan, self.receipt = self._provision(self.instance)

    def tearDown(self):
        self._drop_schema(self.plan)
        super().tearDown()

    def test_single_field_uniqueness_still_enforced_independently(self):
        self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/",
            {str(self.name_field.id): "A", str(self.price_field.id): "1.00", str(self.sku_field.id): "SKU1"},
            format="json",
        )
        dupe_sku = self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/",
            {str(self.name_field.id): "B", str(self.price_field.id): "2.00", str(self.sku_field.id): "SKU1"},
            format="json",
        )
        self.assertEqual(dupe_sku.status_code, 400, dupe_sku.data)

    def test_composite_uniqueness_still_enforced_independently(self):
        self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/",
            {str(self.name_field.id): "A", str(self.price_field.id): "1.00", str(self.sku_field.id): "SKU1"},
            format="json",
        )
        dupe_pair = self.client.post(
            f"/api/v1/app-models/{self.item.id}/records/",
            {str(self.name_field.id): "A", str(self.price_field.id): "1.00", str(self.sku_field.id): "SKU2"},
            format="json",
        )
        self.assertEqual(dupe_pair.status_code, 400, dupe_pair.data)


class LiveAdditionTestBase(ProvisioningTestBase):
    def setUp(self):
        super().setUp()
        self.instance = self._install(sample())
        self.item = self.instance.models.get(key="item")
        self.group = self.instance.models.get(key="group")
        self.name_field = self.item.fields.get(key="name")
        self.price_field = self.item.fields.get(key="price")
        self.plan, self.receipt = self._provision(self.instance)

    def tearDown(self):
        self._drop_schema(self.plan)
        super().tearDown()

    def _add_constraint(self, model_id, field_ids, key="name_price_unique", label="Unique Name+Price"):
        return self.client.post(
            f"/api/v1/app-models/{model_id}/constraints/",
            {"key": key, "label": label, "field_ids": [str(f) for f in field_ids]},
            format="json",
        )


class LiveAdditionCleanDataTests(LiveAdditionTestBase):
    def test_populated_clean_model_can_add_a_composite_constraint(self):
        self._create(self.item.id, self.name_field, self.price_field, "A", "1.00")
        self._create(self.item.id, self.name_field, self.price_field, "B", "1.00")

        resp = self._add_constraint(self.item.id, [self.name_field.id, self.price_field.id])
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(
            {str(f) for f in resp.data["field_ids"]}, {str(self.name_field.id), str(self.price_field.id)}
        )

        dupe = self._create(self.item.id, self.name_field, self.price_field, "A", "1.00")
        self.assertEqual(dupe.status_code, 400, dupe.data)

    def test_adding_an_unpopulated_model_constraint_works_too(self):
        resp = self._add_constraint(self.item.id, [self.name_field.id, self.price_field.id])
        self.assertEqual(resp.status_code, 201, resp.data)


class LiveAdditionDuplicateDataTests(LiveAdditionTestBase):
    def test_populated_duplicate_model_rejects_the_constraint_safely(self):
        self._create(self.item.id, self.name_field, self.price_field, "Dupe", "5.00")
        self._create(self.item.id, self.name_field, self.price_field, "Dupe", "5.00")

        resp = self._add_constraint(self.item.id, [self.name_field.id, self.price_field.id])
        self.assertEqual(resp.status_code, 400, resp.data)
        # No physical/definition constraint left behind on failure.
        leftover = ConstraintDefinition.objects.filter(model=self.item, key="name_price_unique")
        self.assertFalse(leftover.exists())

    def test_existing_duplicate_data_is_completely_untouched(self):
        self._create(self.item.id, self.name_field, self.price_field, "Dupe", "5.00")
        self._create(self.item.id, self.name_field, self.price_field, "Dupe", "5.00")
        self._add_constraint(self.item.id, [self.name_field.id, self.price_field.id])

        listing = self.client.get(f"/api/v1/app-models/{self.item.id}/records/")
        self.assertEqual(listing.data["count"], 2)

    def test_schema_remains_usable_after_a_failed_constraint_addition(self):
        self._create(self.item.id, self.name_field, self.price_field, "Dupe", "5.00")
        self._create(self.item.id, self.name_field, self.price_field, "Dupe", "5.00")
        self._add_constraint(self.item.id, [self.name_field.id, self.price_field.id])

        still_works = self._create(self.item.id, self.name_field, self.price_field, "Fresh", "9.00")
        self.assertEqual(still_works.status_code, 201, still_works.data)

    def test_error_does_not_leak_row_values(self):
        self._create(self.item.id, self.name_field, self.price_field, "SecretName", "42.00")
        self._create(self.item.id, self.name_field, self.price_field, "SecretName", "42.00")
        resp = self._add_constraint(self.item.id, [self.name_field.id, self.price_field.id])
        self.assertEqual(resp.status_code, 400)
        self.assertNotIn("SecretName", str(resp.data))


class LiveAdditionValidationTests(LiveAdditionTestBase):
    def test_invalid_cross_model_field_reference_is_rejected(self):
        # "group" has no fields of its own in sample() -- add one so
        # there's a genuinely different model's real field id to try.
        group_field = self.client.post(
            f"/api/v1/app-models/{self.group.id}/fields/",
            {"key": "label", "label": "Label", "data_type": "text"},
            format="json",
        ).data
        resp = self._add_constraint(self.item.id, [self.name_field.id, group_field["id"]])
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(ConstraintDefinition.objects.filter(model=self.item).exists())

    def test_repeated_field_id_is_rejected(self):
        resp = self._add_constraint(self.item.id, [self.name_field.id, self.name_field.id])
        self.assertEqual(resp.status_code, 400)

    def test_missing_field_reference_is_rejected(self):
        resp = self._add_constraint(self.item.id, [self.name_field.id, uuid.uuid4()])
        self.assertEqual(resp.status_code, 400)

    def test_single_field_constraint_is_rejected(self):
        resp = self._add_constraint(self.item.id, [self.name_field.id])
        self.assertEqual(resp.status_code, 400)


class IdempotentReprovisioningTests(LiveAdditionTestBase):
    def test_reapplying_the_same_constraint_to_the_runtime_is_idempotent(self):
        resp = self._add_constraint(self.item.id, [self.name_field.id, self.price_field.id])
        self.assertEqual(resp.status_code, 201, resp.data)
        constraint = ConstraintDefinition.objects.get(pk=resp.data["id"])

        self.receipt.refresh_from_db()
        before = self.receipt.bindings["constraints"][str(constraint.id)]
        # Directly re-invoke the schema-evolution primitive, as a retry
        # after a crash between the DDL committing and the bindings save
        # would -- must not raise, and must not create a second index.
        # Same transaction/flag sequencing instances.add_constraint itself
        # uses (mark_addition_transaction() before the receipt is touched)
        # since the control-plane trigger guard requires it.
        with transaction.atomic():
            schema_evolution.mark_addition_transaction()
            with transaction.atomic(using="tenant"):
                schema_evolution.add_constraint_to_runtime(self.receipt, constraint, self.actor)
        self.receipt.refresh_from_db()
        after = self.receipt.bindings["constraints"][str(constraint.id)]
        self.assertEqual(before, after)
        self.assertEqual(DBIndex.objects.filter(pk=before).count(), 1)


class StabilityTests(LiveAdditionTestBase):
    def setUp(self):
        super().setUp()
        resp = self._add_constraint(self.item.id, [self.name_field.id, self.price_field.id])
        self.constraint = ConstraintDefinition.objects.get(pk=resp.data["id"])
        self.receipt.refresh_from_db()
        self.index_id_before = self.receipt.bindings["constraints"][str(self.constraint.id)]

    def test_renaming_the_constraint_label_does_not_recreate_it(self):
        resp = self.client.patch(
            f"/api/v1/app-constraints/{self.constraint.id}/", {"label": "Renamed"}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.receipt.refresh_from_db()
        self.assertEqual(self.receipt.bindings["constraints"][str(self.constraint.id)], self.index_id_before)

        # Still functions after the rename.
        self._create(self.item.id, self.name_field, self.price_field, "X", "1.00")
        dupe = self._create(self.item.id, self.name_field, self.price_field, "X", "1.00")
        self.assertEqual(dupe.status_code, 400)

    def test_reordering_a_participating_field_does_not_recreate_the_constraint(self):
        resp = self.client.patch(
            f"/api/v1/app-fields/{self.price_field.id}/", {"position": 0}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.receipt.refresh_from_db()
        self.assertEqual(self.receipt.bindings["constraints"][str(self.constraint.id)], self.index_id_before)

        self._create(self.item.id, self.name_field, self.price_field, "Y", "2.00")
        dupe = self._create(self.item.id, self.name_field, self.price_field, "Y", "2.00")
        self.assertEqual(dupe.status_code, 400)


class TenantIsolationTests(LiveAdditionTestBase):
    def test_a_member_without_the_capability_cannot_add_a_constraint(self):
        outsider = User.objects.create_user(email="cx-outsider@example.com")
        Membership.objects.create(user=outsider, organization=self.org, status=Membership.Status.ACTIVE)
        client = APIClient()
        client.force_authenticate(outsider)

        resp = client.post(
            f"/api/v1/app-models/{self.item.id}/constraints/",
            {
                "key": "outsider_attempt",
                "label": "Outsider",
                "field_ids": [str(self.name_field.id), str(self.price_field.id)],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(ConstraintDefinition.objects.filter(key="outsider_attempt").exists())

        grant_resource_permission(
            user=outsider,
            permission_code="app_instance.schema.manage",
            organization_id=self.org.id,
            resource_type="app_instance",
            resource_id=self.instance.id,
        )
        assign_role(user=outsider, role_slug="database-administrator", organization=self.org)
        allowed = client.post(
            f"/api/v1/app-models/{self.item.id}/constraints/",
            {
                "key": "outsider_attempt",
                "label": "Outsider",
                "field_ids": [str(self.name_field.id), str(self.price_field.id)],
            },
            format="json",
        )
        self.assertEqual(allowed.status_code, 201, allowed.data)

    def test_a_non_member_cannot_read_a_constraint_by_id_substitution(self):
        resp = self._add_constraint(self.item.id, [self.name_field.id, self.price_field.id])
        constraint_id = resp.data["id"]

        outsider = User.objects.create_user(email="cx-nonmember@example.com")
        create_organization(name="CX Outsider Org", created_by=outsider)
        client = APIClient()
        client.force_authenticate(outsider)

        detail = client.get(f"/api/v1/app-constraints/{constraint_id}/")
        self.assertEqual(detail.status_code, 404)

    def test_direct_unsanctioned_orm_write_to_constraint_fields_is_still_blocked_once_provisioned(self):
        """Security review parity with test_field_indexing.py's own
        direct-ORM-write test: the 0012 trigger guards are a real
        backstop, not merely enforced by instances.py/schema_evolution.py
        at the Python layer. A label-only change is legitimately exempt
        (see app_runtime_definition_guard's own label/position carve-out,
        unchanged by this feature and already covered by StabilityTests
        above) -- this test targets the genuinely new mutable surface
        0012 introduced: the constraint's field-membership through table."""
        resp = self._add_constraint(self.item.id, [self.name_field.id, self.price_field.id])
        constraint = ConstraintDefinition.objects.get(pk=resp.data["id"])

        with self.assertRaises(Exception) as ctx:
            ConstraintDefinition.objects.filter(pk=constraint.id).update(model=self.group)
        self.assertIn("Reserved runtime definitions require a schema migration", str(ctx.exception))

        other_field = self.client.post(
            f"/api/v1/app-models/{self.item.id}/fields/",
            {"key": "notes", "label": "Notes", "data_type": "text"},
            format="json",
        ).data
        with self.assertRaises(Exception) as ctx:
            constraint.fields.add(other_field["id"])
        self.assertIn("Reserved runtime constraint fields require a schema migration", str(ctx.exception))
