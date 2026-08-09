import uuid

from django.conf import settings
from django.db import models


class ShareGrant(models.Model):
    """Records that a resource was shared with a principal (User/Team/
    Organization) at a given level. This is the human-facing "who shared
    what with whom" record — it is not a second enforcement path.
    Enforcement is entirely the existing `permissions.ResourceGrant`/
    `has_permission` mechanism (docs/architecture/DATA_MODEL.md Section
    3.8; permissions/models.py's `ResourceGrant` docstring: "Used for
    internal sharing (Phase 9) and for restricting an Application's scope
    to specific resources (Phase 7) — the same mechanism, per ADR-0008").
    `sharing/services.py` creates one `ResourceGrant` per (target user,
    permission code) implied by `level` when a `ShareGrant` is created,
    and removes them on revoke.

    External sharing (expiring links, passwords, IP restriction) is
    deliberately not modeled here yet — Phase 9 ships only the
    per-organization `external_sharing_enabled` toggle (see
    `organizations.Organization`) as scaffolding; DATA_MODEL.md Section
    3.8 calls for it to be a later addition to *this* table via nullable
    columns, not a parallel model, once actually built."""

    class Level(models.TextChoices):
        READ = "read", "Read"
        WRITE = "write", "Write"
        ADMIN = "admin", "Admin"

    class PrincipalType(models.TextChoices):
        USER = "user", "User"
        TEAM = "team", "Team"
        ORGANIZATION = "organization", "Organization"
        # "role" (DATA_MODEL.md Section 3.8) is deliberately not
        # implemented — sharing with an abstract role, rather than a
        # concrete user/team/org, has no clear precedent elsewhere in
        # this codebase's authorization model and no further spec detail
        # to build against; left as an explicit open item rather than a
        # silent omission (see docs/architecture/ROADMAP.md Phase 9).

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="share_grants"
    )
    resource_type = models.CharField(max_length=100)
    resource_id = models.UUIDField()
    principal_type = models.CharField(max_length=20, choices=PrincipalType.choices)
    # Exactly one of user/team is set, matching principal_type; validated
    # in sharing/services.py rather than a DB CHECK constraint, consistent
    # with how this codebase validates elsewhere (e.g. DBColumn default
    # values) in the service layer, not the schema.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="share_grants_received",
        null=True,
        blank=True,
    )
    team = models.ForeignKey(
        "organizations.Team",
        on_delete=models.CASCADE,
        related_name="share_grants_received",
        null=True,
        blank=True,
    )
    level = models.CharField(max_length=20, choices=Level.choices)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="share_grants_created",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["resource_type", "resource_id"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        principal = self.user_id or self.team_id or self.organization_id
        return f"{self.resource_type}:{self.resource_id} -> {self.principal_type}:{principal} ({self.level})"
