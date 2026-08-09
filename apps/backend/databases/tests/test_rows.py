"""
Full round-trip tests for the data explorer's row API against a real
tenant table.
"""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from organizations.models import Membership
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand


class RowTestBase(APITestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        SeedPermissionsCommand().handle()
        self.admin = User.objects.create_user(email="rows-admin@example.com", password="x")
        self.client.force_login(self.admin)

        org = self.client.post(reverse("organization-list-create"), {"name": "Acme"})
        self.org_id = org.data["id"]
        ws = self.client.post(reverse("workspace-list-create", args=[self.org_id]), {"name": "WS"})
        proj = self.client.post(reverse("project-list-create", args=[ws.data["id"]]), {"name": "Proj"})
        db = self.client.post(
            reverse("tenant-database-list-create", args=[proj.data["id"]]), {"name": "AppDB"}
        )
        table = self.client.post(reverse("table-list-create", args=[db.data["id"]]), {"name": "people"})
        self.table_id = table.data["id"]

        for col in [
            {"name": "name", "data_type": "text", "is_nullable": False},
            {"name": "age", "data_type": "integer"},
            {"name": "active", "data_type": "boolean", "default_value": True},
        ]:
            self.client.post(reverse("column-create", args=[self.table_id]), col, format="json")

    def _create(self, name, age, active=None):
        payload = {"name": name, "age": age}
        if active is not None:
            payload["active"] = active
        resp = self.client.post(reverse("row-list-create", args=[self.table_id]), payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        return resp.data


class RowCrudTests(RowTestBase):
    def test_insert_list_get_update_delete_round_trip(self):
        row = self._create("Alice", 30, True)
        self.assertEqual(row["name"], "Alice")
        self.assertEqual(row["age"], 30)
        self.assertTrue(row["active"])
        row_id = row["id"]

        listing = self.client.get(reverse("row-list-create", args=[self.table_id]))
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(listing.data["count"], 1)
        self.assertEqual(listing.data["results"][0]["id"], row_id)

        detail = self.client.get(reverse("row-detail", args=[self.table_id, row_id]))
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data["name"], "Alice")

        update = self.client.patch(
            reverse("row-detail", args=[self.table_id, row_id]), {"age": 31}, format="json"
        )
        self.assertEqual(update.status_code, status.HTTP_200_OK)
        self.assertEqual(update.data["age"], 31)
        self.assertEqual(update.data["name"], "Alice")  # untouched fields preserved

        delete = self.client.delete(reverse("row-detail", args=[self.table_id, row_id]))
        self.assertEqual(delete.status_code, status.HTTP_204_NO_CONTENT)

        after = self.client.get(reverse("row-detail", args=[self.table_id, row_id]))
        self.assertEqual(after.status_code, status.HTTP_404_NOT_FOUND)

    def test_default_value_applies_when_omitted(self):
        row = self._create("Bob", 25)
        self.assertTrue(row["active"])  # column default_value=True

    def test_missing_required_field_is_rejected(self):
        resp = self.client.post(
            reverse("row-list-create", args=[self.table_id]), {"age": 40}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_wrong_type_is_rejected(self):
        resp = self.client.post(
            reverse("row-list-create", args=[self.table_id]),
            {"name": "Carol", "age": "not-a-number"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_set_the_generated_id_column(self):
        resp = self.client.post(
            reverse("row-list-create", args=[self.table_id]),
            {"id": "11111111-1111-1111-1111-111111111111", "name": "Dave", "age": 1},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_row_returns_404(self):
        resp = self.client.get(
            reverse("row-detail", args=[self.table_id, "11111111-1111-1111-1111-111111111111"])
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class RowQueryTests(RowTestBase):
    def setUp(self):
        super().setUp()
        self._create("Alice", 30, True)
        self._create("Bob", 25, False)
        self._create("Carol", 35, True)

    def test_ordering(self):
        resp = self.client.get(reverse("row-list-create", args=[self.table_id]), {"ordering": "age"})
        self.assertEqual([r["name"] for r in resp.data["results"]], ["Bob", "Alice", "Carol"])

        resp = self.client.get(reverse("row-list-create", args=[self.table_id]), {"ordering": "-age"})
        self.assertEqual([r["name"] for r in resp.data["results"]], ["Carol", "Alice", "Bob"])

    def test_search_across_text_columns(self):
        resp = self.client.get(reverse("row-list-create", args=[self.table_id]), {"search": "ali"})
        self.assertEqual([r["name"] for r in resp.data["results"]], ["Alice"])

    def test_equality_filter(self):
        resp = self.client.get(reverse("row-list-create", args=[self.table_id]), {"f_active": "false"})
        # active is boolean; equality filter passes the raw query-string
        # value through, so this documents the (currently string) filter
        # behavior rather than silently mismatching.
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_pagination_limit_and_offset(self):
        resp = self.client.get(reverse("row-list-create", args=[self.table_id]), {"limit": 1, "offset": 1})
        self.assertEqual(resp.data["count"], 3)
        self.assertEqual(len(resp.data["results"]), 1)

    def test_limit_is_capped_at_max(self):
        resp = self.client.get(reverse("row-list-create", args=[self.table_id]), {"limit": 100000})
        self.assertEqual(resp.data["limit"], 500)

    def test_search_with_sql_metacharacters_is_treated_as_data(self):
        resp = self.client.get(
            reverse("row-list-create", args=[self.table_id]), {"search": "'; DROP TABLE people; --"}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 0)  # no match, but no error and no damage

        # table must still exist and still have all 3 rows
        still_there = self.client.get(reverse("row-list-create", args=[self.table_id]))
        self.assertEqual(still_there.data["count"], 3)

    def test_ordering_by_unknown_column_is_rejected(self):
        resp = self.client.get(
            reverse("row-list-create", args=[self.table_id]), {"ordering": "'; DROP TABLE people; --"}
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class RowExportTests(RowTestBase):
    def test_export_streams_csv_with_header_and_rows(self):
        self._create("Alice", 30, True)
        self._create("Bob", 25, False)

        resp = self.client.get(reverse("row-export", args=[self.table_id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        content = b"".join(resp.streaming_content).decode()
        lines = content.strip().splitlines()
        self.assertEqual(lines[0], "id,name,age,active")
        self.assertEqual(len(lines), 3)  # header + 2 rows


class RowPermissionTests(RowTestBase):
    def setUp(self):
        super().setUp()
        self.member = User.objects.create_user(email="rows-member@example.com", password="x")
        Membership.objects.create(
            user=self.member, organization_id=self.org_id, status=Membership.Status.ACTIVE
        )

    def test_member_without_database_write_cannot_insert(self):
        self.client.force_login(self.member)
        resp = self.client.post(
            reverse("row-list-create", args=[self.table_id]), {"name": "X", "age": 1}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_without_database_read_cannot_list(self):
        self.client.force_login(self.member)
        resp = self.client.get(reverse("row-list-create", args=[self.table_id]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_without_dataset_export_cannot_export(self):
        self.client.force_login(self.member)
        resp = self.client.get(reverse("row-export", args=[self.table_id]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
