"""One read-only call for an instance's whole schema (models + fields + relationships).

The customer screens used to fetch the schema with 2 + N requests per page load (N = number of models: 15
for Spare Parts), which -- found by the accessibility run -- exhausts the per-user rate limit (300/minute)
after ~20 page loads. This endpoint returns the same information in one request and a constant number of
queries. It must equal the composition of the three existing list endpoints and enforce the same access.
"""

from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from accounts.models import User
from app_platform import instances, templates
from app_platform.reference_templates.spare_parts import spare_parts_reference_definition
from app_platform.tests.test_foundation import project_for, sample
from organizations.models import Membership
from organizations.services import create_organization


class InstanceSchemaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_permissions", verbosity=0)
        cls.owner = User.objects.create_user(email="schema-owner@example.com")
        cls.org = create_organization(name="Schema Org", created_by=cls.owner)
        cls.project = project_for(cls.owner, cls.org)

    def _install(self, label, draft):
        template = templates.create_template(self.owner, self.org, {"label": label, "draft": draft})
        version = templates.publish_template(self.owner, template)
        return instances.install(
            self.owner, self.project, {"label": label, "template_version": str(version.id)}
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.owner)

    def _schema(self, instance):
        response = self.client.get(f"/api/v1/app-instances/{instance.id}/schema/")
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_it_equals_the_composition_of_the_three_list_endpoints(self):
        instance = self._install("Spare Parts", spare_parts_reference_definition())
        schema = self._schema(instance)

        models = self.client.get(f"/api/v1/app-instances/{instance.id}/models/?limit=100").data["results"]
        relationships = self.client.get(f"/api/v1/app-instances/{instance.id}/relationships/?limit=100").data[
            "results"
        ]
        self.assertEqual([m["id"] for m in schema["models"]], [m["id"] for m in models])
        self.assertEqual(schema["relationships"], relationships)
        for model in schema["models"]:
            expected = self.client.get(f"/api/v1/app-models/{model['id']}/fields/?limit=100").data["results"]
            self.assertEqual(model["fields"], expected, model["key"])
            self.assertEqual(
                {k: model[k] for k in ("id", "key", "label")},
                {k: next(m for m in models if m["id"] == model["id"])[k] for k in ("id", "key", "label")},
            )

    def test_the_query_count_does_not_grow_with_the_number_of_models(self):
        small = self._install("Small", sample())
        large = self._install("Large", spare_parts_reference_definition())
        self._schema(small)  # warm-up: the first call pays one-time costs (permission cache, content types)
        counts = []
        for instance in (small, large):
            with CaptureQueriesContext(connection) as queries:
                self._schema(instance)
            counts.append(len(queries))
        self.assertEqual(counts[0], counts[1], f"queries per model count: {counts}")  # no N+1
        self.assertLess(counts[1], 20)

    def test_another_organizations_user_gets_not_found(self):
        instance = self._install("Private", sample())
        outsider = User.objects.create_user(email="schema-outsider@example.com")
        create_organization(name="Elsewhere", created_by=outsider)
        client = APIClient()
        client.force_authenticate(outsider)
        self.assertEqual(client.get(f"/api/v1/app-instances/{instance.id}/schema/").status_code, 404)

    def test_a_member_without_read_access_is_denied_like_the_list_endpoints(self):
        instance = self._install("Guarded", sample())
        member = User.objects.create_user(email="schema-member@example.com")
        Membership.objects.create(user=member, organization=self.org, status=Membership.Status.ACTIVE)
        client = APIClient()
        client.force_authenticate(member)
        listing = client.get(f"/api/v1/app-instances/{instance.id}/models/")
        schema = client.get(f"/api/v1/app-instances/{instance.id}/schema/")
        self.assertEqual(schema.status_code, listing.status_code)
        self.assertEqual(schema.status_code, 403)

    def test_it_is_read_only(self):
        instance = self._install("ReadOnly", sample())
        self.assertEqual(
            self.client.post(f"/api/v1/app-instances/{instance.id}/schema/", {}, format="json").status_code,
            405,
        )
