from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from organizations.models import Organization
from permissions.models import Permission, ResourceGrant, Role, RoleAssignment
from permissions.services import (
    PermissionError_,
    assign_role,
    get_user_organization_ids,
    has_permission,
)


class HasPermissionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="u@example.com", password="x")
        self.org = Organization.objects.create(name="Org", slug="org", created_by=self.user)
        self.perm = Permission.objects.create(code="storage.read", description="read")
        self.role = Role.objects.create(slug="reader", name="Reader", organization=None)
        self.role.permissions.add(self.perm)

    def test_denied_with_no_role_assignment(self):
        self.assertFalse(has_permission(self.user, "storage.read", organization_id=self.org.id))

    def test_granted_via_org_scoped_role_assignment(self):
        RoleAssignment.objects.create(user=self.user, role=self.role, organization=self.org)
        self.assertTrue(has_permission(self.user, "storage.read", organization_id=self.org.id))

    def test_org_scoped_role_does_not_leak_to_another_org(self):
        other_org = Organization.objects.create(name="Other", slug="other", created_by=self.user)
        RoleAssignment.objects.create(user=self.user, role=self.role, organization=self.org)
        self.assertFalse(has_permission(self.user, "storage.read", organization_id=other_org.id))

    def test_platform_wide_role_assignment_grants_everywhere(self):
        RoleAssignment.objects.create(user=self.user, role=self.role, organization=None)
        self.assertTrue(has_permission(self.user, "storage.read", organization_id=self.org.id))
        other_org = Organization.objects.create(name="Other", slug="other-2", created_by=self.user)
        self.assertTrue(has_permission(self.user, "storage.read", organization_id=other_org.id))

    def test_resource_grant_authorizes_without_a_role(self):
        ResourceGrant.objects.create(
            user=self.user,
            permission=self.perm,
            organization=self.org,
            resource_type="storage.folder",
            resource_id="11111111-1111-1111-1111-111111111111",
        )
        self.assertFalse(has_permission(self.user, "storage.read", organization_id=self.org.id))
        self.assertTrue(
            has_permission(
                self.user,
                "storage.read",
                organization_id=self.org.id,
                resource=("storage.folder", "11111111-1111-1111-1111-111111111111"),
            )
        )

    def test_expired_resource_grant_does_not_authorize(self):
        ResourceGrant.objects.create(
            user=self.user,
            permission=self.perm,
            organization=self.org,
            resource_type="storage.folder",
            resource_id="11111111-1111-1111-1111-111111111111",
            expires_at=timezone.now() - timedelta(days=1),
        )
        self.assertFalse(
            has_permission(
                self.user,
                "storage.read",
                organization_id=self.org.id,
                resource=("storage.folder", "11111111-1111-1111-1111-111111111111"),
            )
        )

    def test_none_user_never_authorized(self):
        self.assertFalse(has_permission(None, "storage.read", organization_id=self.org.id))


class AssignRoleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="u2@example.com", password="x")
        self.org = Organization.objects.create(name="Org2", slug="org2", created_by=self.user)
        Role.objects.create(slug="super-administrator", name="Super Administrator", organization=None)
        Role.objects.create(slug="viewer", name="Viewer", organization=None)

    def test_platform_wide_assignment_allowed_only_for_super_administrator(self):
        with self.assertRaises(PermissionError_):
            assign_role(user=self.user, role_slug="viewer", organization=None)

    def test_platform_wide_assignment_allowed_for_super_administrator(self):
        assignment = assign_role(user=self.user, role_slug="super-administrator", organization=None)
        self.assertIsNone(assignment.organization)

    def test_org_scoped_assignment_allowed_for_any_role(self):
        assignment = assign_role(user=self.user, role_slug="viewer", organization=self.org)
        self.assertEqual(assignment.organization, self.org)


class GetUserOrganizationIdsTests(TestCase):
    def test_only_org_scoped_assignments_count(self):
        user = User.objects.create_user(email="u3@example.com", password="x")
        org = Organization.objects.create(name="Org3", slug="org3", created_by=user)
        role = Role.objects.create(slug="viewer2", name="Viewer2", organization=None)
        RoleAssignment.objects.create(user=user, role=role, organization=org)
        RoleAssignment.objects.create(user=user, role=role, organization=None)  # platform-wide
        self.assertEqual(get_user_organization_ids(user), {org.id})
