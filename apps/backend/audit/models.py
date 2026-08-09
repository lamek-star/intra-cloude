import uuid

from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    class Result(models.TextChoices):
        SUCCESS = "success", "Success"
        DENIED = "denied", "Denied"
        ERROR = "error", "Error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    action = models.CharField(max_length=100)  # e.g. "database.schema.create"
    resource_type = models.CharField(max_length=100, blank=True)
    resource_id = models.CharField(max_length=64, blank=True)
    request_id = models.CharField(max_length=64, blank=True)
    result = models.CharField(max_length=20, choices=Result.choices)
    # Non-sensitive extra detail only — never passwords, secrets, or full
    # personal data payloads (Section 18 of the master prompt).
    context = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["organization", "-timestamp"]),
            models.Index(fields=["actor", "-timestamp"]),
        ]

    def __str__(self):
        return f"{self.action} by {self.actor_id} -> {self.result}"
