import uuid

from django.conf import settings
from django.db import models


class ImportJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(
        "storage.FileObject", on_delete=models.PROTECT, related_name="import_jobs"
    )
    table = models.ForeignKey("databases.DBTable", on_delete=models.CASCADE, related_name="import_jobs")

    # Encoding/delimiter are detected once during the preview step and
    # confirmed by the client when the job is created — the import task
    # trusts these rather than re-sniffing mid-stream (a streamed S3 body
    # can't be rewound to re-sample after the fact).
    encoding = models.CharField(max_length=20)
    delimiter = models.CharField(max_length=1)
    # [{"csv_column": "...", "target_column": "...", "target_type": "..."}]
    column_mapping = models.JSONField()

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    total_rows = models.PositiveIntegerField(null=True, blank=True)
    imported_rows = models.PositiveIntegerField(default=0)
    rejected_rows = models.PositiveIntegerField(default=0)
    # Enables a retried job to skip rows already committed rather than
    # re-importing them (Section 11 of the master prompt: "resumable/
    # retryable job behavior where technically reasonable").
    last_processed_row = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="import_jobs_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Import {self.id} -> {self.table} ({self.status})"

    @property
    def organization_id(self):
        return self.table.organization_id


class ImportJobError(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(ImportJob, on_delete=models.CASCADE, related_name="errors")
    row_number = models.PositiveIntegerField()
    message = models.CharField(max_length=500)
    raw_row = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["row_number"]

    def __str__(self):
        return f"row {self.row_number}: {self.message}"
