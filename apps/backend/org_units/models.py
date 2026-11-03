import uuid

from django.conf import settings
from django.db import models

from organizations.models import Organization


class OrganizationalUnit(models.Model):
    """A node in an organization's own structural hierarchy (branch,
    campus, department, warehouse, team, or any other label the
    organization chooses -- `unit_type` is a free-form descriptive label,
    never a hardcoded enum, so this stays a generic primitive rather than
    baking one industry's vocabulary into the platform, matching the
    App Platform's own "no industry-specific concept in the core" rule
    (see docs/implementation/APP_PLATFORM_PHASE4.md).

    Deliberately separate from organizations.Team: Team is an existing
    flat, single-parent-per-membership grouping used by unrelated
    sharing/permission code paths, and is left untouched. This is an
    additive, generic tree for Phase 6 (docs/implementation/
    APP_PLATFORM_ROADMAP.md) -- a user can belong to any number of units
    at once via UnitMembership below, unlike Team."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="units")
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="children",
        null=True,
        blank=True,
        help_text="Must belong to the same organization; cycles are rejected at the service layer.",
    )
    unit_type = models.CharField(max_length=100)
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="org_units_created",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "parent", "name"], name="unique_org_unit_name_per_parent"
            ),
        ]
        ordering = ["organization", "name"]

    def __str__(self):
        return f"{self.organization.name} / {self.name}"


class UnitMembership(models.Model):
    """A user's placement in a unit. Many-to-many by design (unlike
    organizations.Membership.team's single nullable FK) -- a person can
    sit in a department and a branch and a team simultaneously."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.ForeignKey(OrganizationalUnit, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="org_unit_memberships"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="org_unit_memberships_created",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["unit", "user"], name="unique_unit_membership"),
        ]
        ordering = ["unit", "user"]

    def __str__(self):
        return f"{self.user} @ {self.unit}"
