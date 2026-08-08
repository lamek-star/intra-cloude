import uuid

from django.conf import settings
from django.db import models


class Permission(models.Model):
    """Static, code-defined capability string (e.g. "storage.read"). The
    catalog is seeded from permissions.catalog.PERMISSIONS via the
    `seed_permissions` management command — never created ad hoc through
    the API (docs/security/PERMISSIONS.md Section 2)."""

    code = models.CharField(max_length=100, primary_key=True)
    description = models.CharField(max_length=255)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.code


class Role(models.Model):
    """A named bundle of Permissions. `organization=None` marks one of the
    seeded system roles (docs/security/PERMISSIONS.md Section 3), usable by
    every organization and never deletable/renamable. An organization may
    later define its own custom roles (organization set, is_system=False)
    — not exercised yet in Phase 2."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="custom_roles",
        null=True,
        blank=True,
    )
    slug = models.SlugField(max_length=100)
    name = models.CharField(max_length=100)
    is_system = models.BooleanField(default=False)
    permissions = models.ManyToManyField(Permission, related_name="roles", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # System roles (organization IS NULL) are globally unique by
            # slug; custom roles are unique per organization. Postgres
            # treats NULL as distinct in a UniqueConstraint, so this needs
            # two constraints rather than one.
            models.UniqueConstraint(
                fields=["slug"],
                condition=models.Q(organization__isnull=True),
                name="unique_system_role_slug",
            ),
            models.UniqueConstraint(
                fields=["organization", "slug"],
                condition=models.Q(organization__isnull=False),
                name="unique_custom_role_slug_per_org",
            ),
        ]
        ordering = ["organization_id", "name"]

    def __str__(self):
        return self.name


class RoleAssignment(models.Model):
    """Grants a Role to a User, either scoped to one Organization or,
    for platform-wide operators, `organization=None`. A null organization
    is only valid when the assigned Role includes `system.admin`
    (enforced in permissions.services.assign_role, not at the DB layer,
    since "which permissions a role has" is data, not schema)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="role_assignments"
    )
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="assignments")
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="role_assignments",
        null=True,
        blank=True,
    )
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="role_assignments_granted",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role", "organization"], name="unique_role_assignment"
            ),
        ]
        ordering = ["user_id"]

    def __str__(self):
        scope = self.organization or "platform-wide"
        return f"{self.user} -> {self.role} ({scope})"


class ResourceGrant(models.Model):
    """Grants exactly one Permission on exactly one resource to one User,
    with an optional expiry. Used for internal sharing (Phase 9) and for
    restricting an Application's scope to specific resources (Phase 7) —
    the same mechanism, per ADR-0008. `resource_type` is a free-form label
    until concrete resource types exist (Phase 3+); nothing in Phase 2
    grants against real resources yet."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="resource_grants"
    )
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name="resource_grants")
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="resource_grants"
    )
    resource_type = models.CharField(max_length=100)
    resource_id = models.UUIDField()
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="resource_grants_granted",
        null=True,
        blank=True,
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["resource_type", "resource_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "permission", "resource_type", "resource_id"],
                name="unique_resource_grant",
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} -> {self.permission_id} on {self.resource_type}:{self.resource_id}"
