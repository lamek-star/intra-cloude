"""`?ids=a,b,c` on the record list: one request that names a page of records.

The customer screens put names next to the ids in a table (a stock row's product and warehouse, a sale's
customer). They used to fetch each name with its own `GET /records/<id>/` -- 36 requests for one Stock page
with 5,000 products -- which is slow and spends the per-user rate limit (300/minute). This is the one-request
form. It must be exactly the ordinary list with an id filter: same permission check, same tenant, no way to
reach a record the caller could not already read.
"""

import uuid

from django.core.management import call_command
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from app_platform.record_views import MAX_IDS
from app_platform.tests.test_quantity_ledger import _LedgerFixture
from app_platform.tests.test_transactions import TransactionBase
from organizations.models import Membership


class RecordIdsLookupTests(TransactionBase):
    def setUp(self):
        super().setUp()
        self.name_field = self._definition_id("part", "name")
        self.parts = [self._create("part", name=f"Part {i}") for i in range(6)]
        self.url = f"/api/v1/app-models/{self.models['part'].id}/records/"

    def _ids(self, *rows):
        return ",".join(str(row["id"]) for row in rows)

    def test_it_returns_exactly_the_named_records_in_one_request(self):
        wanted = [self.parts[1], self.parts[4]]
        response = self.client.get(self.url, {"ids": self._ids(*wanted)})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(
            sorted(row[self.name_field] for row in response.data["results"]), ["Part 1", "Part 4"]
        )

    def test_unknown_and_missing_ids_simply_match_nothing(self):
        response = self.client.get(self.url, {"ids": f"{uuid.uuid4()},{self.parts[0]['id']}"})
        self.assertEqual([row["id"] for row in response.data["results"]], [self.parts[0]["id"]])
        empty = self.client.get(self.url, {"ids": ""})
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(empty.data["count"], 0)

    def test_the_query_count_does_not_grow_with_the_number_of_ids(self):
        self.client.get(self.url, {"ids": self._ids(self.parts[0])})  # warm-up
        counts = []
        for group in (self.parts[:1], self.parts):
            with CaptureQueriesContext(connection) as queries:
                self.client.get(self.url, {"ids": self._ids(*group)})
            counts.append(len(queries))
        self.assertEqual(counts[0], counts[1], counts)

    def test_bad_input_is_a_clear_400_never_a_500(self):
        self.assertEqual(self.client.get(self.url, {"ids": "not-a-uuid"}).status_code, 400)
        self.assertEqual(self.client.get(self.url, {"ids": f"{self.parts[0]['id']},oops"}).status_code, 400)
        too_many = ",".join(str(uuid.uuid4()) for _ in range(MAX_IDS + 1))
        self.assertEqual(self.client.get(self.url, {"ids": too_many}).status_code, 400)
        exactly_max = ",".join(str(uuid.uuid4()) for _ in range(MAX_IDS))
        self.assertEqual(self.client.get(self.url, {"ids": exactly_max}).status_code, 200)
        both = self.client.get(self.url, {"ids": self.parts[0]["id"], "id": self.parts[1]["id"]})
        self.assertEqual(both.status_code, 400)

    def test_it_combines_with_the_other_list_options(self):
        response = self.client.get(self.url, {"ids": self._ids(*self.parts), "search": "Part 3", "limit": 5})
        self.assertEqual([row[self.name_field] for row in response.data["results"]], ["Part 3"])
        paged = self.client.get(self.url, {"ids": self._ids(*self.parts), "limit": 2, "offset": 4})
        self.assertEqual(paged.data["count"], 6)
        self.assertEqual(len(paged.data["results"]), 2)


class RecordIdsLookupAccessTests(TransactionBase):
    def setUp(self):
        super().setUp()
        self.member = User.objects.create_user(email="ids-member@example.com")
        Membership.objects.create(user=self.member, organization=self.org, status=Membership.Status.ACTIVE)
        self.member_client = APIClient()
        self.member_client.force_authenticate(self.member)
        self.url = f"/api/v1/app-models/{self.models['part'].id}/records/"

    def test_a_member_without_read_access_is_refused_and_told_nothing(self):
        response = self.member_client.get(self.url, {"ids": self.part["id"]})
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("count", response.data or {})

    def test_read_access_on_one_model_does_not_open_another(self):
        call_command("seed_permissions", verbosity=0)
        grant = self.client.post(
            reverse("share-grant-list-create", args=[self.org.id]),
            {
                "resource_type": "app_model",
                "resource_id": str(self.models["part"].id),
                "principal_type": "user",
                "user_id": str(self.member.id),
                "level": "read",
            },
            format="json",
        )
        self.assertEqual(grant.status_code, 201, grant.data)
        self.assertEqual(self.member_client.get(self.url, {"ids": self.part["id"]}).data["count"], 1)
        other = f"/api/v1/app-models/{self.models['warehouse'].id}/records/"
        self.assertEqual(self.member_client.get(other, {"ids": self.warehouse["id"]}).status_code, 403)

    def test_another_organizations_record_ids_match_nothing(self):
        foreign = _LedgerFixture.build("ids-foreign@example.com", "Ids Foreign Org")
        try:
            name = str(foreign.item_model.fields.get(key="name").id)
            made = foreign.client.post(
                f"/api/v1/app-models/{foreign.item_model.id}/records/", {name: "Secret"}, format="json"
            )
            self.assertEqual(made.status_code, 201, made.data)
            # Our own model, our own tenant schema: the foreign id simply is not there.
            response = self.client.get(self.url, {"ids": made.data["id"]})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["count"], 0)
            # ...and naming THEIR model's endpoint is simply not found for us, not a leak.
            theirs = f"/api/v1/app-models/{foreign.item_model.id}/records/"
            self.assertEqual(self.client.get(theirs, {"ids": made.data["id"]}).status_code, 404)
        finally:
            foreign.drop_schema()
