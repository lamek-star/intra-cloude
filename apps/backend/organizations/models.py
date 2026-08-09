import uuid

from django.conf import settings
from django.db import models


class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    # Off by default (Phase 9; docs/architecture/adr — sharing). A second,
    # per-organization gate on top of the deployment-wide
    # FEATURE_EXTERNAL_SHARING_ENABLED env flag (config/settings/base.py):
    # the operator must allow the feature for the whole deployment *and*
    # each organization must separately opt in. Toggling this is itself
    # an audited action (sharing/services.py:set_external_sharing_enabled).
    external_sharing_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="organizations_created"
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Team(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="teams")
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], name="unique_team_name_per_org"),
        ]
        ordering = ["name"]

    def __str__(self):
        return f"{self.organization.name} / {self.name}"


class Membership(models.Model):
    class Status(models.TextChoices):
        INVITED = "invited", "Invited"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="memberships")
    team = models.ForeignKey(
        Team, on_delete=models.SET_NULL, related_name="memberships", null=True, blank=True
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="memberships_invited",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "organization"], name="unique_membership_per_org"),
        ]
        ordering = ["organization", "user"]

    def __str__(self):
        return f"{self.user} @ {self.organization} ({self.status})"
