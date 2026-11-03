"""Normalized part-number search on the Spare Parts application's OWN Part Number
records (Local Edition v1.0 flagship requirement).

A part number is typed and printed many ways -- `04465-0K290`, `044650K290`,
`04465 0K290` -- and the shop must find it whichever way it is entered. The
stored/displayed value is never changed; only the match is normalized, with the
one shared rule (`databases.normalization`) that `catalogue_storage` also uses.
"""

import time

from django.core.management import call_command
from django.db import connections
from django.test import SimpleTestCase
from django.urls import reverse
from psycopg import sql
from rest_framework.test import APIClient

from accounts.models import User
from app_platform import schema_evolution
from app_platform.tests.test_quantity_ledger import _LedgerFixture
from app_platform.tests.test_transactions import TransactionBase
from catalogue_storage.models import normalize_part_number
from databases.normalization import normalize_search_key
from organizations.models import Membership


class NormalizationRuleTests(SimpleTestCase):
    def test_hyphen_whitespace_and_case_variants_share_one_key(self):
        variants = [
            "04465-0K290",
            "044650K290",
            "04465 0K290",
            "04465-0k290",
            "  04465  0K290 ",
            "04465\t0K290",
        ]
        self.assertEqual({normalize_search_key(v) for v in variants}, {"044650K290"})

    def test_a_non_breaking_space_is_whitespace_too(self):
        self.assertEqual(normalize_search_key("04465 0K290"), "044650K290")

    def test_other_characters_are_kept(self):
        self.assertEqual(normalize_search_key("AB.12/3"), "AB.12/3")
        self.assertEqual(normalize_search_key(""), "")
        self.assertEqual(normalize_search_key(" - "), "")

    def test_catalogue_storage_uses_the_same_rule(self):
        for value in ("15690-65010", "1569065010", "15690 65010", "ab-1 2"):
            self.assertEqual(normalize_part_number(value), normalize_search_key(value))


class PartNumberSearchTests(TransactionBase):
    def setUp(self):
        super().setUp()
        self.number_field = self._definition_id("part_number", "number")
        self.part_rel = self._definition_id("part_number", "part_number_part")
        self.brake = self._create("part", name="Brake Pad Set")
        self.pn = self._create(
            "part_number", number="04465-0K290", source="OEM", part_number_part=self.brake["id"]
        )
        self._create("part_number", number="OF-1001", source="OEM", part_number_part=self.part["id"])

    def _search(self, query, client=None):
        response = (client or self.client).get(
            f"/api/v1/app-models/{self.models['part_number'].id}/records/",
            {"search": query},
        )
        return response

    def _numbers(self, query):
        response = self._search(query)
        self.assertEqual(response.status_code, 200, response.data)
        return sorted(row[self.number_field] for row in response.data["results"])

    def test_exact_search_finds_the_part_number(self):
        self.assertEqual(self._numbers("04465-0K290"), ["04465-0K290"])

    def test_every_written_variant_finds_the_same_record(self):
        for variant in ("044650K290", "04465 0K290", "04465-0k290", "  04465  0K290 ", "04465-0K290"):
            with self.subTest(variant=variant):
                self.assertEqual(self._numbers(variant), ["04465-0K290"])

    def test_a_partial_number_matches_however_it_is_written(self):
        for fragment in ("04465", "0K290", "4465 0K", "44650k2"):
            with self.subTest(fragment=fragment):
                self.assertEqual(self._numbers(fragment), ["04465-0K290"])

    def test_the_original_display_value_is_never_changed(self):
        rows = self._search("044650K290").data["results"]
        self.assertEqual(rows[0][self.number_field], "04465-0K290")

    def test_the_result_leads_back_to_its_part(self):
        rows = self._search("044650K290").data["results"]
        self.assertEqual(rows[0][self.part_rel], self.brake["id"])

    def test_no_match_returns_nothing(self):
        self.assertEqual(self._numbers("99999-99999"), [])

    def test_a_query_of_only_separators_does_not_match_everything(self):
        self.assertEqual(self._numbers(" - "), [])

    def test_ambiguous_variants_are_all_returned_not_silently_merged(self):
        # The stored numbers differ as text, so the unique constraint allows both.
        self._create(
            "part_number", number="044650K290", source="Aftermarket", part_number_part=self.brake["id"]
        )
        self.assertEqual(self._numbers("04465-0K290"), ["04465-0K290", "044650K290"])
        self.assertEqual(self._search("04465 0K290").data["count"], 2)

    def test_like_wildcards_in_the_query_are_literal(self):
        self._create("part_number", number="A_B", source="x", part_number_part=self.brake["id"])
        self._create("part_number", number="AXB", source="x", part_number_part=self.brake["id"])
        self.assertEqual(self._numbers("A_B"), ["A_B"])
        self.assertEqual(self._numbers("A%B"), [])
        self.assertEqual(self._numbers("%"), [])

    def test_search_still_finds_ordinary_words_in_other_fields(self):
        response = self.client.get(
            f"/api/v1/app-models/{self.models['part'].id}/records/", {"search": "brake"}
        )
        names = [row[self._definition_id("part", "name")] for row in response.data["results"]]
        self.assertEqual(names, ["Brake Pad Set"])

    def test_search_and_pagination_counts_agree(self):
        for index in range(7):
            self._create(
                "part_number", number=f"ZZ-{index:03d}", source="x", part_number_part=self.brake["id"]
            )
        response = self.client.get(
            f"/api/v1/app-models/{self.models['part_number'].id}/records/", {"search": "zz 0", "limit": 3}
        )
        self.assertEqual(response.data["count"], 7)
        self.assertEqual(len(response.data["results"]), 3)


class PartNumberSearchAccessTests(TransactionBase):
    def setUp(self):
        super().setUp()
        self._create("part_number", number="04465-0K290", source="OEM", part_number_part=self.part["id"])
        self.member = User.objects.create_user(email="search-member@example.com")
        Membership.objects.create(user=self.member, organization=self.org, status=Membership.Status.ACTIVE)
        self.member_client = APIClient()
        self.member_client.force_authenticate(self.member)
        self.url = f"/api/v1/app-models/{self.models['part_number'].id}/records/"

    def test_a_member_without_read_access_cannot_search(self):
        self.assertEqual(self.member_client.get(self.url, {"search": "044650K290"}).status_code, 403)

    def test_a_member_granted_read_can_search_and_only_that_model(self):
        call_command("seed_permissions", verbosity=0)
        response = self.client.post(
            reverse("share-grant-list-create", args=[self.org.id]),
            {
                "resource_type": "app_model",
                "resource_id": str(self.models["part_number"].id),
                "principal_type": "user",
                "user_id": str(self.member.id),
                "level": "read",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self.member_client.get(self.url, {"search": "044650K290"}).data["count"], 1)
        other = f"/api/v1/app-models/{self.models['part'].id}/records/"
        self.assertEqual(self.member_client.get(other, {"search": "oil"}).status_code, 403)

    def test_another_organizations_data_is_unreachable_by_search_or_by_id(self):
        foreign = _LedgerFixture.build("search-foreign@example.com", "Search Foreign Org")
        try:
            name = str(foreign.item_model.fields.get(key="name").id)
            foreign.client.post(
                f"/api/v1/app-models/{foreign.item_model.id}/records/", {name: "04465-0K290"}, format="json"
            )
            # Our own search sees only our own tenant schema...
            mine = self.client.get(self.url, {"search": "044650K290"})
            self.assertEqual(mine.data["count"], 1)
            # ...and pointing at the other organization's model by id is simply not found.
            theirs = f"/api/v1/app-models/{foreign.item_model.id}/records/"
            self.assertEqual(self.client.get(theirs, {"search": "044650K290"}).status_code, 404)
        finally:
            foreign.drop_schema()


class PartNumberSearchScaleTests(TransactionBase):
    """A small shop's realistic catalogue: 10,000 part numbers. Normalized matching is
    evaluated per row (no index -- a b-tree cannot serve a contains-match on a
    transformed value), so this proves it stays correct and comfortably fast at that
    size, and records the plan; add an expression index only if this ever regresses."""

    def test_ten_thousand_part_numbers_search_correctly_and_quickly(self):
        model = self.models["part_number"]
        table = schema_evolution._table_for(self.receipt, model)
        column = schema_evolution._column_for(self.receipt, model.fields.get(key="number"))
        target = sql.SQL("{}.{}").format(
            sql.Identifier(table.tenant_database.schema_name), sql.Identifier(table.name)
        )
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL(
                    "INSERT INTO {} ({}) "
                    "SELECT 'ZZ-' || lpad(g::text, 6, '0') FROM generate_series(1, 10000) g"
                ).format(target, sql.Identifier(column.name))
            )
            cursor.execute(
                sql.SQL("INSERT INTO {} ({}) VALUES ('04465-0K290')").format(
                    target, sql.Identifier(column.name)
                )
            )
            cursor.execute("ANALYZE")
        url = f"/api/v1/app-models/{model.id}/records/"
        started = time.perf_counter()
        response = self.client.get(url, {"search": "04465 0k290"})
        elapsed = time.perf_counter() - started
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0][self._definition_id("part_number", "number")], "04465-0K290"
        )
        print(f"SCALE: normalized search over 10,001 part numbers: {elapsed * 1000:.0f} ms")
        self.assertLess(elapsed, 2.0)
        # a broad query still pages correctly at this size
        broad = self.client.get(url, {"search": "zz 0000", "limit": 50})
        # ZZ-000001 .. ZZ-000099 are the only numbers that begin ZZ0000
        self.assertEqual(broad.data["count"], 99)
        self.assertEqual(len(broad.data["results"]), 50)
