import uuid

from django.conf import settings
from django.db import models


class ExportJob(models.Model):
    """One .icp portable-export package build for one Organization (the
    only export_type implemented so far — Section 14 of the master
    prompt lists several narrower scopes as future work). The finished
    package is written to object storage, not the control-plane
    database — this row is metadata/status only (ADR-0001)."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="export_jobs"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="export_jobs_created"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    encrypted = models.BooleanField(default=False)
    # Set once COMPLETED — the object-storage key of the finished .icp
    # package (never a local filesystem path; ADR-0001).
    object_key = models.CharField(max_length=255, blank=True)
    size_bytes = models.BigIntegerField(null=True, blank=True)
    checksum_sha256 = models.CharField(max_length=64, blank=True)
    error_message = models.CharField(max_length=2000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Export {self.id} ({self.organization_id}) — {self.status}"


class RestoreJob(models.Model):
    """One .icp import/restore attempt. `organization` is null until the
    restore actually creates the new Organization (Section 17 of the
    master prompt: nothing should be visible/reachable until the whole
    restore either fully commits or fully rolls back) — see
    exports/restorer.py."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        VALIDATING = "validating", "Validating"
        RESTORING = "restoring", "Restoring"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="restore_jobs",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="restore_jobs_created"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    # The uploaded .icp package, staged in object storage until the
    # restore either completes or fails (then it's deleted either way —
    # it isn't a backup of itself).
    source_object_key = models.CharField(max_length=255)
    # Populated on completion: what was restored, what was skipped and
    # why (e.g. a membership whose user has no account on this
    # installation) — Section 17's "final restore report", never silent
    # about anything dropped.
    report = models.JSONField(default=dict, blank=True)
    error_message = models.CharField(max_length=2000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Restore {self.id} — {self.status}"
