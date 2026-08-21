import uuid

from django.db import models


class BackupRecord(models.Model):
    """One `pg_dump` attempt against a control-plane or tenant PostgreSQL
    connection (system/backups.py). `verified_restorable` is never set
    True by the backup itself — only a subsequent, independent restore-
    and-validate pass against an isolated database sets it
    (docs/operations/BACKUP_RESTORE.md Section 6/7: "a backup strategy is
    not considered complete until restoration has actually been
    tested")."""

    class BackupType(models.TextChoices):
        CONTROL_DB = "control_db", "Control-Plane Database"
        TENANT_DB = "tenant_db", "Tenant Database"
        OBJECT_STORAGE = "object_storage", "Object Storage"
        CONFIGURATION = "configuration", "Configuration"

    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    backup_type = models.CharField(max_length=20, choices=BackupType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RUNNING)
    file_path = models.CharField(max_length=500, blank=True)
    size_bytes = models.BigIntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    verified_restorable = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_error = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.backup_type} backup {self.id} ({self.status})"
