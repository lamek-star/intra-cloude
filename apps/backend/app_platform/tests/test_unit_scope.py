"""Phase 7 Step 3 ("unit scope", docs/implementation/APP_PLATFORM_PHASE7.md):
a UnitScopedGrant restricts a user to one model's records whose
org_unit_reference field matches one specific OrganizationalUnit --
genuine row-level filtering, the first thing in this platform that
restricts access to a *subset* of a resource's rows rather than the whole
resource. Exercised entirely through the real record CRUD API and the
real grant/revoke endpoints, as different real users, not by calling
service functions directly."""

import uuid

from django.core.management import call_command
from django.db import connections
from django.test import TransactionTestCase
from psycopg import sql
from rest_framework.test import APIClient

from accounts.models import User
from app_platform import instances, provisioning, templates
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for
from app_platform.tests.test_org_unit_reference_field import org_unit_reference_sample
from org_units.models import OrganizationalUnit
from organizations.models import Membership
from organizations.services import create_organization


class UnitScopeTestBase(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.owner = User.objects.create_user(email="uscope-owner@example.com")
        self.org = create_organization(name="Unit Scope Org", created_by=self.owner)
        self.project = project_for(self.owner, self.org)
        template = templates.create_template(
            self.owner, self.org, {"label": "App", "draft": org_unit_reference_sample()}
        )
        version = templates.publish_template(self.owner, template)
        self.instance = instances.install(
            self.owner, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )
        self.task = self.instance.models.get(key="task")
        self.name_field = self.task.fields.get(key="name")
        self.unit_field = self.task.fields.get(key="owning_unit")

        self.plan = plan_runtime(self.owner, self.instance)
        provisioning.reserve(self.owner, self.instance, self.plan["fingerprint"])
        self.receipt = provisioning.execute(self.instance.id, self.owner)

        self.unit_a = OrganizationalUnit.objects.create(
            organization=self.org, name="Unit A", unit_type="branch", created_by=self.owner
        )
        self.unit_b = OrganizationalUnit.objects.create(
            organization=self.org, name="Unit B", unit_type="branch", created_by=self.owner
        )

        self.member = User.objects.create_user(email="uscope-member@example.com")
        Membership.objects.create(user=self.member, organization=self.org, status=Membership.Status.ACTIVE)

        self.owner_client = APIClient()
        self.owner_client.force_authenticate(self.owner)
        self.member_client = APIClient()
        self.member_client.force_authenticate(self.member)

        self.a_record_id = self._create_as_owner(self.unit_a.id)["id"]
        self.b_record_id = self._create_as_owner(self.unit_b.id)["id"]

    def tearDown(self):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.plan["schema_name"]))
            )
        super().tearDown()

    def _create_as_owner(self, unit_id):
        resp = self.owner_client.post(
            f"/api/v1/app-models/{self.task.id}/records/",
            {str(self.name_field.id): "Task", str(self.unit_field.id): str(unit_id)},
            format="json",
        )
        assert resp.status_code == 201, resp.data
        return resp.data

    def _grant(self, unit_id, level, **overrides):
        payload = {"user_id": str(self.member.id), "unit_id": str(unit_id), "level": level}
        payload.update(overrides)
        return self.owner_client.post(f"/api/v1/app-models/{self.task.id}/unit-grants/", payload, format="json")

    def _records_url(self):
        return f"/api/v1/app-models/{self.task.id}/records/"

    def _detail_url(self, record_id):
        return f"{self._records_url()}{record_id}/"


class NoGrantTests(UnitScopeTestBase):
    def test_a_plain_member_has_no_access_at_all(self):
        self.assertEqual(self.member_client.get(self._records_url()).status_code, 403)
        self.assertEqual(
            self.member_client.post(self._records_url(), {}, format="json").status_code, 403
        )


class ReadLevelTests(UnitScopeTestBase):
    def test_read_level_lists_only_the_granted_unit(self):
        grant = self._grant(self.unit_a.id, "read")
        self.assertEqual(grant.status_code, 201, grant.data)

        listing = self.member_client.get(self._records_url())
        self.assertEqual(listing.status_code, 200)
        ids = {r["id"] for r in listing.data["results"]}
        self.assertEqual(ids, {self.a_record_id})

    def test_read_level_cannot_create(self):
        self._grant(self.unit_a.id, "read")
        resp = self.member_client.post(
            self._records_url(),
            {str(self.name_field.id): "New", str(self.unit_field.id): str(self.unit_a.id)},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_read_level_can_get_a_record_in_the_granted_unit(self):
        self._grant(self.unit_a.id, "read")
        resp = self.member_client.get(self._detail_url(self.a_record_id))
        self.assertEqual(resp.status_code, 200)

    def test_read_level_cannot_get_a_record_outside_the_granted_unit(self):
        self._grant(self.unit_a.id, "read")
        resp = self.member_client.get(self._detail_url(self.b_record_id))
        self.assertEqual(resp.status_code, 403)


class WriteLevelTests(UnitScopeTestBase):
    def setUp(self):
        super().setUp()
        grant = self._grant(self.unit_a.id, "write")
        assert grant.status_code == 201, grant.data

    def test_can_create_within_the_granted_unit(self):
        resp = self.member_client.post(
            self._records_url(),
            {str(self.name_field.id): "Mine", str(self.unit_field.id): str(self.unit_a.id)},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_cannot_create_in_a_different_unit(self):
        resp = self.member_client.post(
            self._records_url(),
            {str(self.name_field.id): "Not mine", str(self.unit_field.id): str(self.unit_b.id)},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_cannot_create_with_no_unit_set(self):
        resp = self.member_client.post(
            self._records_url(), {str(self.name_field.id): "Unscoped"}, format="json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_cannot_delete_a_record_outside_the_granted_unit(self):
        resp = self.member_client.delete(self._detail_url(self.b_record_id))
        self.assertEqual(resp.status_code, 403)

    def test_can_delete_a_record_inside_the_granted_unit(self):
        resp = self.member_client.delete(self._detail_url(self.a_record_id))
        self.assertEqual(resp.status_code, 204)

    def test_cannot_reassign_a_record_to_a_unit_outside_the_grant(self):
        resp = self.member_client.patch(
            self._detail_url(self.a_record_id), {str(self.unit_field.id): str(self.unit_b.id)}, format="json"
        )
        self.assertEqual(resp.status_code, 403)
        # The rejected update must not have moved the record.
        still_a = self.owner_client.get(self._detail_url(self.a_record_id))
        self.assertEqual(str(still_a.data[str(self.unit_field.id)]), str(self.unit_a.id))

    def test_can_update_a_record_within_the_granted_unit_without_touching_its_unit(self):
        resp = self.member_client.patch(
            self._detail_url(self.a_record_id), {str(self.name_field.id): "Renamed"}, format="json"
        )
        self.assertEqual(resp.status_code, 200, resp.data)


class RevocationTests(UnitScopeTestBase):
    def test_revoking_a_grant_removes_access_immediately(self):
        grant = self._grant(self.unit_a.id, "read")
        grant_id = grant.data["id"]

        self.assertEqual(self.member_client.get(self._detail_url(self.a_record_id)).status_code, 200)

        revoke = self.owner_client.delete(f"/api/v1/app-unit-grants/{grant_id}/")
        self.assertEqual(revoke.status_code, 204)

        self.assertEqual(self.member_client.get(self._detail_url(self.a_record_id)).status_code, 403)


class GrantValidationTests(UnitScopeTestBase):
    def test_a_plain_member_cannot_create_a_grant(self):
        other = User.objects.create_user(email="uscope-other@example.com")
        Membership.objects.create(user=other, organization=self.org, status=Membership.Status.ACTIVE)
        client = APIClient()
        client.force_authenticate(self.member)
        resp = client.post(
            f"/api/v1/app-models/{self.task.id}/unit-grants/",
            {"user_id": str(other.id), "unit_id": str(self.unit_a.id), "level": "read"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_granting_on_a_model_with_more_than_one_org_unit_reference_field_is_rejected(self):
        # unit_reference_field() requires exactly one such field to avoid
        # "restricted to unit X" being ambiguous about which field it
        # means -- add a second one to task (which already has
        # owning_unit) to exercise that rejection.
        second = self.owner_client.post(
            f"/api/v1/app-models/{self.task.id}/fields/",
            {"key": "second_unit", "label": "Second Unit", "data_type": "org_unit_reference"},
            format="json",
        )
        self.assertEqual(second.status_code, 201, second.data)

        resp = self._grant(self.unit_a.id, "read")
        self.assertEqual(resp.status_code, 400, resp.data)

    def test_granting_a_unit_from_another_organization_is_rejected(self):
        other_org = create_organization(name="Other Unit Scope Org", created_by=self.owner)
        foreign_unit = OrganizationalUnit.objects.create(
            organization=other_org, name="Foreign", unit_type="branch", created_by=self.owner
        )
        resp = self._grant(foreign_unit.id, "read")
        self.assertEqual(resp.status_code, 404)

    def test_granting_to_a_non_member_is_rejected(self):
        outsider = User.objects.create_user(email="uscope-outsider@example.com")
        resp = self.owner_client.post(
            f"/api/v1/app-models/{self.task.id}/unit-grants/",
            {"user_id": str(outsider.id), "unit_id": str(self.unit_a.id), "level": "read"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.data)


class CrossOrgIsolationTests(UnitScopeTestBase):
    def test_a_non_member_cannot_revoke_a_grant_by_id_substitution(self):
        grant = self._grant(self.unit_a.id, "read")
        outsider = User.objects.create_user(email="uscope-nonmember@example.com")
        create_organization(name="Unit Scope Outsider Org", created_by=outsider)
        outsider_client = APIClient()
        outsider_client.force_authenticate(outsider)

        resp = outsider_client.delete(f"/api/v1/app-unit-grants/{grant.data['id']}/")
        self.assertEqual(resp.status_code, 404)

    def test_a_non_member_cannot_list_grants_by_id_substitution(self):
        outsider = User.objects.create_user(email="uscope-nonmember2@example.com")
        create_organization(name="Unit Scope Outsider Org 2", created_by=outsider)
        outsider_client = APIClient()
        outsider_client.force_authenticate(outsider)

        resp = outsider_client.get(f"/api/v1/app-models/{self.task.id}/unit-grants/")
        self.assertEqual(resp.status_code, 404)
