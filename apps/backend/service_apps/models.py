"""Separately deployed service applications (ADR-0018).

A ServiceApp is one installed instance of an application type (`spare_parts`,
`intraforge_pay`, `pharmacy`) that runs as its own service but keeps its data, files,
identity, audit and configuration in IntraForge.
"""

import uuid

from django.conf import settings
from django.db import models


class ServiceApp(models.Model):
    class AppType(models.TextChoices):
        SPARE_PARTS = "spare_parts", "Spare Parts"
        INTRAFORGE_PAY = "intraforge_pay", "IntraForge Pay"
        PHARMACY = "pharmacy", "Pharmacy"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="service_apps"
    )
    project = models.ForeignKey("workspaces.Project", on_delete=models.PROTECT, related_name="service_apps")
    # The service deployment slot this instance runs in (a key of settings.SERVICE_APP_DEPLOYMENTS).
    # One slot holds at most one instance: the service process serves exactly one schema.
    deployment = models.CharField(max_length=63, unique=True)
    app_type = models.CharField(max_length=40, choices=AppType.choices)
    # What the Apps page shows (the configured shop name by default). Never hard-coded.
    display_name = models.CharField(max_length=200)
    # Validated per app type (service_apps.types); never holds secrets.
    config = models.JSONField(default=dict)
    enabled = models.BooleanField(default=True)
    # "Removed, data kept": hidden from Apps and closed to everyone, schema and files retained so
    # it can be reinstated (or restored). Only an explicit data deletion frees the slot.
    removed_at = models.DateTimeField(null=True, blank=True)
    # The PostgreSQL schema in the tenant database that holds the application's data. It is owned
    # by the deployment's own login role and is deliberately NOT a databases.TenantDatabase, so the
    # visual database builder can never edit an application's tables behind its business rules.
    schema_name = models.CharField(max_length=63, unique=True)
    bucket = models.OneToOneField("storage.Bucket", on_delete=models.PROTECT, related_name="service_app")
    # Reported by the service itself (heartbeat); informational.
    reported_version = models.CharField(max_length=64, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="service_apps_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_name"]

    def __str__(self):
        return f"{self.display_name} ({self.get_app_type_display()})"


class ServiceAppSession(models.Model):
    """A browser session for one service application, minted by "Open" in IntraForge.

    The raw token lives only in an HttpOnly cookie scoped to the application's path; this row
    stores its SHA-256. It is bound to the user's IntraForge session, so logging out of IntraForge
    (or any change that invalidates that session) ends it too.
    """

    id = models.BigAutoField(primary_key=True)
    token_hash = models.CharField(max_length=64, unique=True)
    service_app = models.ForeignKey(ServiceApp, on_delete=models.CASCADE, related_name="sessions")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="service_app_sessions"
    )
    django_session_key = models.CharField(max_length=40, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["service_app", "user"])]

    def __str__(self):
        return f"session {self.pk} for {self.user_id} on {self.service_app_id}"


class ServiceAppAuditReceipt(models.Model):
    """Makes audit relay idempotent: the service sends each event at least once, identified by the
    id it gave the event in its own transactional log; IntraForge records it exactly once."""

    event_id = models.CharField(max_length=64, primary_key=True)
    service_app = models.ForeignKey(ServiceApp, on_delete=models.CASCADE, related_name="audit_receipts")
    audit_event = models.ForeignKey("audit.AuditEvent", on_delete=models.PROTECT)
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.event_id
