"""
Per-application Environment management: Organization -> Application ->
Environment, per docs/architecture/ROADMAP.md's Environment Management
subsystem entry. An Environment is the isolation boundary a Development
credential must never cross into Production — `is_production_tier` (not
`environment_type`, a free-form label) is the field every isolation and
RBAC check in this app and in databases/storage actually keys off, so a
future custom environment kind can opt into the same protection without
a schema change.

Deliberately does NOT hold its own FK to the TenantDatabase/Bucket it
uses — those apps hold a nullable FK back to `Environment` instead
(databases.TenantDatabase.environment, storage.Bucket.environment),
matching this codebase's established "child points to parent" FK
direction (TenantDatabase.project, Bucket.project) and, just as
importantly, keeping this app's own models.py free of any FK into
`databases`/`storage`, so only they depend on `environments` — not the
other way around.
"""

import uuid

from django.conf import settings
from django.db import models


class EnvironmentType(models.TextChoices):
    """First-class kinds with UI treatment out of the box. Not a hard
    DB-level enum — `environment_type` is a plain CharField (see below),
    so a future custom kind is a new choice tuple here, not a migration.
    Whether a kind gets Production's extra protection is the separate
    `is_production_tier` flag, not this string."""

    DEVELOPMENT = "development", "Development"
    STAGING = "staging", "Staging"
    PRODUCTION = "production", "Production"
    CUSTOM = "custom", "Custom"


class Environment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        DISABLED = "disabled", "Disabled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        "applications.Application", on_delete=models.CASCADE, related_name="environments"
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    environment_type = models.CharField(
        max_length=30, choices=EnvironmentType.choices, default=EnvironmentType.DEVELOPMENT
    )
    # The actual security-relevant flag (RBAC's environment.production.manage
    # gate, cross-environment isolation checks) — defaulted from
    # environment_type at creation time (services.create_environment) but
    # stored independently so it can't silently drift if environment_type's
    # choices ever change, and so a CUSTOM environment can still be marked
    # production-tier.
    is_production_tier = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    # Non-secret structured configuration only (service endpoints, auth
    # config like allowed origins/redirect URIs) -- secret values always
    # go through EnvironmentSecret, never here.
    config = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="environments_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["application", "slug"], name="unique_environment_slug_per_application"
            ),
        ]
        ordering = ["application_id", "name"]

    def __str__(self):
        return f"{self.application} / {self.name}"

    @property
    def organization_id(self):
        return self.application.organization_id


class EnvironmentVariable(models.Model):
    """Plain, non-secret configuration (e.g. LOG_LEVEL=debug). Secret
    values never belong here — see EnvironmentSecret."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    environment = models.ForeignKey(Environment, on_delete=models.CASCADE, related_name="variables")
    key = models.CharField(max_length=200)
    value = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["environment", "key"], name="unique_environment_variable_key"),
        ]
        ordering = ["key"]

    def __str__(self):
        return f"{self.environment} / {self.key}"


class EnvironmentSecret(models.Model):
    """Never stores a plaintext value -- only a Fernet ciphertext
    (environments/crypto.py, same CREDENTIAL_ENCRYPTION_KEY-derived key as
    accounts/databases' equivalent modules). The plaintext is known only
    at creation/rotation time, in the API response body for that one
    request, and is never logged, never included in an audit event
    context, and never re-displayed by any read endpoint afterward."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    environment = models.ForeignKey(Environment, on_delete=models.CASCADE, related_name="secrets")
    key = models.CharField(max_length=200)
    value_ciphertext = models.BinaryField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="environment_secrets_created",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    rotated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["environment", "key"], name="unique_environment_secret_key"),
        ]
        ordering = ["key"]

    def __str__(self):
        return f"{self.environment} / {self.key} (secret)"


class EnvironmentWebhook(models.Model):
    """The signing secret is encrypted the same way EnvironmentSecret's
    values are -- never returned by a read endpoint after creation."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    environment = models.ForeignKey(Environment, on_delete=models.CASCADE, related_name="webhooks")
    url = models.URLField(max_length=500)
    event_types = models.JSONField(default=list, blank=True)
    enabled = models.BooleanField(default=True)
    signing_secret_ciphertext = models.BinaryField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="environment_webhooks_created",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.environment} webhook -> {self.url}"
