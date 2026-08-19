import uuid

from django.conf import settings
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver


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
            models.Index(fields=["organization", "action", "-timestamp"]),
        ]

    def __str__(self):
        return f"{self.action} by {self.actor_id} -> {self.result}"

    def save(self, *args, **kwargs):
        # Audit events are append-only (Section 40 of the master prompt:
        # "protect audit records from ordinary user modification"). Once
        # an instance has round-tripped through the database, nothing
        # short of a direct database session may change it — the ORM
        # path is closed here, not just left to convention.
        if not self._state.adding:
            raise ValueError("AuditEvent records are immutable and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("AuditEvent records cannot be deleted through the ORM.")


@receiver(pre_delete, sender=AuditEvent)
def _forbid_audit_event_deletion(sender, **kwargs):
    # Belt-and-suspenders alongside the instance-level delete() override
    # above: Django's QuerySet.delete() (a bulk SQL DELETE) never calls
    # an instance's delete() method, but it does emit pre_delete for
    # every row being removed — including cascaded/bulk deletes — so
    # this is the one place that actually covers `AuditEvent.objects
    # .filter(...).delete()` too, not just `event.delete()`.
    raise ValueError("AuditEvent records cannot be deleted through the ORM.")
