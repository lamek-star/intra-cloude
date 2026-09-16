"""Phase 6 -- organizational hierarchy (docs/implementation/
APP_PLATFORM_ROADMAP.md): a generic OrganizationalUnit tree per
organization (branches/campuses/departments/warehouses/teams are example
`unit_type` labels, not a hardcoded enum) plus UnitMembership. The two
exit-bar invariants -- cycle prevention and organization isolation -- get
dedicated test classes; the rest exercises the ordinary CRUD/permission/
audit shape every other resource in this codebase follows."""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from audit.models import AuditEvent
from organizations.models import Membership
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand


class OrgUnitTestBase(APITestCase):
    def setUp(self):
        SeedPermissionsCommand().handle()
        self.admin = User.objects.create_user(email="unit-admin@example.com", password="x")
        self.client.force_login(self.admin)
        org = self.client.post(reverse("organization-list-create"), {"name": "Acme"})
        self.org_id = org.data["id"]

    def _create_unit(self, name, unit_type="department", parent=None):
        payload = {"name": name, "unit_type": unit_type}
        if parent is not None:
            payload["parent"] = parent
        resp = self.client.post(reverse("org-unit-list-create", args=[self.org_id]), payload, format="json")
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        return resp.data["id"]

    def _add_plain_member(self, email):
        member = User.objects.create_user(email=email, password="x")
        Membership.objects.create(user=member, organization_id=self.org_id, status=Membership.Status.ACTIVE)
        return member


class CreateAndListTests(OrgUnitTestBase):
    def test_create_root_and_child_and_list_flat(self):
        root = self._create_unit("Headquarters", unit_type="branch")
        child = self._create_unit("Sales", unit_type="department", parent=root)

        listing = self.client.get(reverse("org-unit-list-create", args=[self.org_id]))
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        names = {u["name"] for u in listing.data}
        self.assertEqual(names, {"Headquarters", "Sales"})
        sales = next(u for u in listing.data if u["id"] == child)
        self.assertEqual(str(sales["parent"]), root)

    def test_tree_endpoint_nests_children(self):
        root = self._create_unit("Headquarters", unit_type="branch")
        self._create_unit("Sales", unit_type="department", parent=root)

        tree = self.client.get(reverse("org-unit-tree", args=[self.org_id]))
        self.assertEqual(tree.status_code, status.HTTP_200_OK)
        self.assertEqual(len(tree.data), 1)
        self.assertEqual(tree.data[0]["name"], "Headquarters")
        self.assertEqual([c["name"] for c in tree.data[0]["children"]], ["Sales"])

    def test_duplicate_name_under_same_parent_is_a_409(self):
        self._create_unit("Sales")
        dup = self.client.post(
            reverse("org-unit-list-create", args=[self.org_id]), {"name": "Sales", "unit_type": "department"}
        )
        self.assertEqual(dup.status_code, status.HTTP_409_CONFLICT)

    def test_create_emits_an_audit_event(self):
        unit_id = self._create_unit("Sales")
        event = AuditEvent.objects.get(action="org_unit.create", resource_id=unit_id)
        self.assertEqual(str(event.organization_id), self.org_id)


class PermissionTests(OrgUnitTestBase):
    def test_plain_member_cannot_create_a_unit(self):
        self._add_plain_member("unit-plain@example.com")
        self.client.force_login(User.objects.get(email="unit-plain@example.com"))
        resp = self.client.post(
            reverse("org-unit-list-create", args=[self.org_id]), {"name": "Sneaky", "unit_type": "team"}
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_plain_member_cannot_list_units(self):
        self._create_unit("Sales")
        self._add_plain_member("unit-plain2@example.com")
        self.client.force_login(User.objects.get(email="unit-plain2@example.com"))
        resp = self.client.get(reverse("org-unit-list-create", args=[self.org_id]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class CycleAndIsolationTests(OrgUnitTestBase):
    """The roadmap's own exit bar for this phase: 'cycle prevention and
    organization isolation.'"""

    def test_a_unit_cannot_become_its_own_parent(self):
        root = self._create_unit("Headquarters")
        resp = self.client.patch(
            reverse("org-unit-detail", args=[root]), {"parent": root}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)

    def test_reparenting_under_a_descendant_is_rejected(self):
        a = self._create_unit("A")
        b = self._create_unit("B", parent=a)
        c = self._create_unit("C", parent=b)

        resp = self.client.patch(reverse("org-unit-detail", args=[a]), {"parent": c}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)

    def test_reparenting_to_a_non_descendant_succeeds(self):
        a = self._create_unit("A")
        b = self._create_unit("B")
        c = self._create_unit("C", parent=a)

        resp = self.client.patch(reverse("org-unit-detail", args=[c]), {"parent": b}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(str(resp.data["parent"]), b)

    def test_moving_a_unit_to_root_with_explicit_null_parent(self):
        a = self._create_unit("A")
        b = self._create_unit("B", parent=a)

        resp = self.client.patch(reverse("org-unit-detail", args=[b]), {"parent": None}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertIsNone(resp.data["parent"])

    def test_a_parent_from_another_organization_is_rejected(self):
        other_org = self.client.post(reverse("organization-list-create"), {"name": "Other Org"})
        other_org_id = other_org.data["id"]
        other_unit = self.client.post(
            reverse("org-unit-list-create", args=[other_org_id]), {"name": "Other Root", "unit_type": "branch"}
        )
        other_unit_id = other_unit.data["id"]

        resp = self.client.post(
            reverse("org-unit-list-create", args=[self.org_id]),
            {"name": "Sales", "unit_type": "department", "parent": other_unit_id},
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_a_non_member_cannot_read_a_unit_by_id_substitution(self):
        unit_id = self._create_unit("Sales")
        outsider = User.objects.create_user(email="unit-outsider@example.com", password="x")
        self.client.force_login(outsider)

        for resp in (
            self.client.get(reverse("org-unit-detail", args=[unit_id])),
            self.client.patch(reverse("org-unit-detail", args=[unit_id]), {"name": "Hijacked"}),
            self.client.delete(reverse("org-unit-detail", args=[unit_id])),
        ):
            self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_a_non_member_cannot_manage_unit_membership_by_id_substitution(self):
        unit_id = self._create_unit("Sales")
        outsider = User.objects.create_user(email="unit-outsider2@example.com", password="x")
        self.client.force_login(outsider)

        resp = self.client.post(
            reverse("org-unit-member-list-create", args=[unit_id]), {"user_id": str(outsider.id)}
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class DeleteTests(OrgUnitTestBase):
    def test_deleting_a_leaf_unit_succeeds(self):
        unit_id = self._create_unit("Sales")
        resp = self.client.delete(reverse("org-unit-detail", args=[unit_id]))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_deleting_a_unit_with_children_is_a_409(self):
        parent_id = self._create_unit("HQ")
        self._create_unit("Sales", parent=parent_id)
        resp = self.client.delete(reverse("org-unit-detail", args=[parent_id]))
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)

    def test_deleting_children_then_the_parent_succeeds(self):
        parent_id = self._create_unit("HQ")
        child_id = self._create_unit("Sales", parent=parent_id)
        self.client.delete(reverse("org-unit-detail", args=[child_id]))
        resp = self.client.delete(reverse("org-unit-detail", args=[parent_id]))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)


class MembershipTests(OrgUnitTestBase):
    def setUp(self):
        super().setUp()
        self.unit_id = self._create_unit("Sales")
        self.member = self._add_plain_member("unit-member@example.com")

    def test_add_and_remove_a_unit_member(self):
        add = self.client.post(
            reverse("org-unit-member-list-create", args=[self.unit_id]), {"user_id": str(self.member.id)}
        )
        self.assertEqual(add.status_code, status.HTTP_201_CREATED, add.data)

        listing = self.client.get(reverse("org-unit-member-list-create", args=[self.unit_id]))
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(len(listing.data), 1)

        remove = self.client.delete(reverse("org-unit-member-detail", args=[self.unit_id, self.member.id]))
        self.assertEqual(remove.status_code, status.HTTP_204_NO_CONTENT)

    def test_adding_a_non_member_of_the_organization_is_a_404(self):
        outsider = User.objects.create_user(email="unit-nonorg@example.com", password="x")
        resp = self.client.post(
            reverse("org-unit-member-list-create", args=[self.unit_id]), {"user_id": str(outsider.id)}
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_a_user_can_belong_to_multiple_units_at_once(self):
        other_unit_id = self._create_unit("Marketing")
        self.client.post(
            reverse("org-unit-member-list-create", args=[self.unit_id]), {"user_id": str(self.member.id)}
        )
        resp = self.client.post(
            reverse("org-unit-member-list-create", args=[other_unit_id]), {"user_id": str(self.member.id)}
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_plain_member_cannot_manage_unit_membership(self):
        self.client.force_login(self.member)
        resp = self.client.post(
            reverse("org-unit-member-list-create", args=[self.unit_id]), {"user_id": str(self.member.id)}
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
