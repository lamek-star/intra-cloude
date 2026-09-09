import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from django.core.management import call_command
from django.db import close_old_connections, connections
from django.test import TransactionTestCase
from psycopg import sql
from rest_framework.test import APIClient

from accounts.models import User
from app_platform import instances, provisioning, templates
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for, sample
from audit.models import AuditEvent
from organizations.models import Membership
from organizations.services import create_organization
from permissions.services import grant_resource_permission


class RecordsTests(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="records-owner@example.com")
        self.org = create_organization(name="Records Org", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        template = templates.create_template(self.actor, self.org, {"label": "App", "draft": sample()})
        version = templates.publish_template(self.actor, template)
        self.instance = instances.install(
            self.actor, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )
        self.plan = plan_runtime(self.actor, self.instance)
        provisioning.reserve(self.actor, self.instance, self.plan["fingerprint"])
        self.receipt = provisioning.execute(self.instance.id, self.actor)

        self.item = self.instance.models.get(key="item")
        self.group = self.instance.models.get(key="group")
        self.name_field = self.item.fields.get(key="name")
        self.price_field = self.item.fields.get(key="price")
        self.group_relation = self.instance.relationships.get(key="group")

        self.items_url = f"/api/v1/app-models/{self.item.id}/records/"
        self.groups_url = f"/api/v1/app-models/{self.group.id}/records/"

        self.client = APIClient()
        self.client.force_authenticate(self.actor)

    def tearDown(self):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.plan["schema_name"]))
            )
        super().tearDown()

    def detail_url(self, record_id):
        return f"{self.items_url}{record_id}/"

    def test_create_list_get_update_delete_round_trip(self):
        create = self.client.post(
            self.items_url,
            {str(self.name_field.id): "Bolt", str(self.price_field.id): "12.50"},
            format="json",
        )
        self.assertEqual(create.status_code, 201, create.data)
        record_id = create.data["id"]
        self.assertEqual(create.data[str(self.name_field.id)], "Bolt")
        self.assertEqual(Decimal(create.data[str(self.price_field.id)]), Decimal("12.50"))

        listing = self.client.get(self.items_url)
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data["count"], 1)
        self.assertEqual(listing.data["results"][0]["id"], record_id)

        detail = self.client.get(self.detail_url(record_id))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data[str(self.name_field.id)], "Bolt")

        update = self.client.patch(
            self.detail_url(record_id), {str(self.name_field.id): "Nut"}, format="json"
        )
        self.assertEqual(update.status_code, 200, update.data)
        self.assertEqual(update.data[str(self.name_field.id)], "Nut")

        delete = self.client.delete(self.detail_url(record_id))
        self.assertEqual(delete.status_code, 204)
        self.assertEqual(self.client.get(self.detail_url(record_id)).status_code, 404)

    def test_filters_search_ordering_and_pagination(self):
        for name, price in [("Alpha", "1.00"), ("Beta", "2.00"), ("Gamma", "3.00")]:
            resp = self.client.post(
                self.items_url,
                {str(self.name_field.id): name, str(self.price_field.id): price},
                format="json",
            )
            self.assertEqual(resp.status_code, 201, resp.data)

        filtered = self.client.get(self.items_url, {str(self.name_field.id): "Beta"})
        self.assertEqual(filtered.data["count"], 1)
        self.assertEqual(filtered.data["results"][0][str(self.name_field.id)], "Beta")

        searched = self.client.get(self.items_url, {"search": "amma"})
        self.assertEqual(searched.data["count"], 1)
        self.assertEqual(searched.data["results"][0][str(self.name_field.id)], "Gamma")

        ascending = self.client.get(self.items_url, {"ordering": str(self.name_field.id)})
        self.assertEqual(
            [r[str(self.name_field.id)] for r in ascending.data["results"]], ["Alpha", "Beta", "Gamma"]
        )

        descending = self.client.get(self.items_url, {"ordering": f"-{self.name_field.id}"})
        self.assertEqual(
            [r[str(self.name_field.id)] for r in descending.data["results"]], ["Gamma", "Beta", "Alpha"]
        )

        paged = self.client.get(
            self.items_url, {"limit": 2, "offset": 1, "ordering": str(self.name_field.id)}
        )
        self.assertEqual(paged.data["count"], 3)
        self.assertEqual(len(paged.data["results"]), 2)
        self.assertEqual(paged.data["results"][0][str(self.name_field.id)], "Beta")

    def test_relationship_round_trips_and_rejects_missing_target(self):
        group = self.client.post(self.groups_url, {}, format="json")
        self.assertEqual(group.status_code, 201, group.data)
        group_id = group.data["id"]

        linked = self.client.post(
            self.items_url,
            {str(self.name_field.id): "Widget", str(self.group_relation.id): group_id},
            format="json",
        )
        self.assertEqual(linked.status_code, 201, linked.data)
        self.assertEqual(linked.data[str(self.group_relation.id)], group_id)

        orphaned = self.client.post(
            self.items_url,
            {str(self.name_field.id): "Orphan", str(self.group_relation.id): str(uuid.uuid4())},
            format="json",
        )
        self.assertEqual(orphaned.status_code, 400, orphaned.data)
        self.assertIn("referenced record does not exist", orphaned.data["detail"])

    def test_required_field_missing_is_rejected(self):
        definition = sample()
        definition["models"][0]["fields"][0]["required"] = True
        template = templates.create_template(self.actor, self.org, {"label": "Required", "draft": definition})
        version = templates.publish_template(self.actor, template)
        instance = instances.install(
            self.actor, self.project, {"label": "Required app", "template_version": str(version.id)}
        )
        plan = plan_runtime(self.actor, instance)
        provisioning.reserve(self.actor, instance, plan["fingerprint"])
        provisioning.execute(instance.id, self.actor)
        try:
            item = instance.models.get(key="item")
            price_field = item.fields.get(key="price")
            response = self.client.post(
                f"/api/v1/app-models/{item.id}/records/", {str(price_field.id): "1.00"}, format="json"
            )
            self.assertEqual(response.status_code, 400, response.data)
        finally:
            with connections["tenant"].cursor() as cursor:
                cursor.execute(
                    sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(plan["schema_name"]))
                )

    def test_decimal_overflow_is_rejected_cleanly(self):
        response = self.client.post(
            self.items_url,
            {str(self.name_field.id): "Too big", str(self.price_field.id): "9" * 20},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(response.data["detail"], "invalid record data")

    def test_unknown_field_id_is_rejected(self):
        response = self.client.post(self.items_url, {str(uuid.uuid4()): "x"}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("unknown field or relationship", response.data["detail"])

    def test_foreign_organization_model_id_is_not_found(self):
        outsider = User.objects.create_user(email="records-outsider@example.com")
        create_organization(name="Other Org", created_by=outsider)
        client = APIClient()
        client.force_authenticate(outsider)
        response = client.get(self.items_url)
        self.assertEqual(response.status_code, 404)

    def test_member_without_database_permission_is_denied(self):
        member = User.objects.create_user(email="records-member@example.com")
        Membership.objects.create(user=member, organization=self.org, status=Membership.Status.ACTIVE)
        client = APIClient()
        client.force_authenticate(member)

        self.assertEqual(client.get(self.items_url).status_code, 403)
        self.assertEqual(
            client.post(self.items_url, {str(self.name_field.id): "x"}, format="json").status_code, 403
        )

        grant_resource_permission(
            user=member,
            permission_code="database.read",
            organization_id=self.org.id,
            resource_type="databases.tenant_database",
            resource_id=self.receipt.database_id,
        )
        self.assertEqual(client.get(self.items_url).status_code, 200)
        self.assertEqual(
            client.post(self.items_url, {str(self.name_field.id): "x"}, format="json").status_code, 403
        )

    def test_unprovisioned_instance_returns_404(self):
        definition = sample()
        template = templates.create_template(
            self.actor, self.org, {"label": "Unprovisioned", "draft": definition}
        )
        version = templates.publish_template(self.actor, template)
        unprovisioned = instances.install(
            self.actor, self.project, {"label": "No runtime", "template_version": str(version.id)}
        )
        model = unprovisioned.models.get(key="item")
        response = self.client.get(f"/api/v1/app-models/{model.id}/records/")
        self.assertEqual(response.status_code, 404)

    def test_record_mutations_are_audited_without_leaking_field_values(self):
        create = self.client.post(self.items_url, {str(self.name_field.id): "Secret name"}, format="json")
        record_id = create.data["id"]
        self.client.patch(self.detail_url(record_id), {str(self.name_field.id): "Renamed"}, format="json")
        self.client.delete(self.detail_url(record_id))

        events = AuditEvent.objects.filter(
            resource_type="app_model", resource_id=str(self.item.id)
        ).order_by("timestamp")
        actions = [event.action for event in events]
        self.assertEqual(
            actions,
            ["app_instance.record.create", "app_instance.record.update", "app_instance.record.delete"],
        )
        for event in events:
            self.assertEqual(event.context.get("record_id"), str(record_id))
            serialized = str(event.context)
            self.assertNotIn("Secret name", serialized)
            self.assertNotIn("Renamed", serialized)

    def test_revoking_the_resource_grant_immediately_denies_access(self):
        member = User.objects.create_user(email="records-revoke@example.com")
        Membership.objects.create(user=member, organization=self.org, status=Membership.Status.ACTIVE)
        client = APIClient()
        client.force_authenticate(member)

        grant = grant_resource_permission(
            user=member,
            permission_code="database.read",
            organization_id=self.org.id,
            resource_type="databases.tenant_database",
            resource_id=self.receipt.database_id,
        )
        self.assertEqual(client.get(self.items_url).status_code, 200)

        grant.delete()
        self.assertEqual(client.get(self.items_url).status_code, 403)

    def test_concurrent_updates_to_the_same_record_do_not_corrupt_it(self):
        create = self.client.post(self.items_url, {str(self.name_field.id): "Start"}, format="json")
        record_id = create.data["id"]

        def update(name):
            close_old_connections()
            client = APIClient()
            client.force_authenticate(User.objects.get(pk=self.actor.pk))
            try:
                payload = {str(self.name_field.id): name}
                return client.patch(self.detail_url(record_id), payload, format="json")
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(update, ["Alpha", "Beta"]))
        for response in responses:
            self.assertEqual(response.status_code, 200, response.data)

        final = self.client.get(self.detail_url(record_id))
        self.assertIn(final.data[str(self.name_field.id)], ["Alpha", "Beta"])

    def test_attachment_from_a_foreign_model_cannot_be_reached_by_id_substitution(self):
        # A second, unrelated app instance/model in the SAME organization --
        # proves the attachment lookup is scoped by (model, record_id), not
        # just organization membership, closing the same class of gap the
        # cross-organization attachment test covers from a different angle.
        template = templates.create_template(self.actor, self.org, {"label": "Other App", "draft": sample()})
        version = templates.publish_template(self.actor, template)
        other_instance = instances.install(
            self.actor, self.project, {"label": "Other Runtime", "template_version": str(version.id)}
        )
        other_plan = plan_runtime(self.actor, other_instance)
        provisioning.reserve(self.actor, other_instance, other_plan["fingerprint"])
        provisioning.execute(other_instance.id, self.actor)
        try:
            other_item = other_instance.models.get(key="item")
            create = self.client.post(self.items_url, {str(self.name_field.id): "Mine"}, format="json")
            record_id = create.data["id"]

            # record_id is real, but belongs to self.item's table, not
            # other_item's -- the lookup must be scoped by (model, record),
            # not accept any record id that merely exists somewhere.
            response = self.client.get(
                f"/api/v1/app-models/{other_item.id}/records/{record_id}/attachments/"
            )
            self.assertEqual(response.status_code, 404)
        finally:
            with connections["tenant"].cursor() as cursor:
                cursor.execute(
                    sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                        sql.Identifier(other_plan["schema_name"])
                    )
                )
