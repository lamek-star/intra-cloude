import uuid

from django.conf import settings
from django.db import models


class Bucket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey("workspaces.Project", on_delete=models.CASCADE, related_name="buckets")
    # Optional binding to an Application Environment -- same OneToOne
    # pattern and rationale as databases.TenantDatabase.environment.
    environment = models.OneToOneField(
        "environments.Environment",
        on_delete=models.SET_NULL,
        related_name="bucket",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=200)
    versioning_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="buckets_created"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "name"], name="unique_bucket_name_per_project"),
        ]
        ordering = ["name"]

    def __str__(self):
        return f"{self.project} / {self.name}"

    @property
    def organization_id(self):
        return self.project.workspace.organization_id


class Folder(models.Model):
    """Virtual hierarchy stored as metadata rows (adjacency list) — never
    a real filesystem directory (docs/architecture/DATA_MODEL.md Section
    3.4)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bucket = models.ForeignKey(Bucket, on_delete=models.CASCADE, related_name="folders")
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, related_name="children", null=True, blank=True
    )
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="folders_created"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["bucket", "parent", "name"], name="unique_folder_name_per_parent"
            ),
        ]
        ordering = ["name"]

    def __str__(self):
        return self.name


class FileObject(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        DELETED = "deleted", "Deleted"
        QUARANTINED = "quarantined", "Quarantined"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bucket = models.ForeignKey(Bucket, on_delete=models.CASCADE, related_name="files")
    folder = models.ForeignKey(
        Folder, on_delete=models.CASCADE, related_name="files", null=True, blank=True
    )
    # Server-generated, never derived from user input (prevents path
    # traversal / key collision — Section 8 of the master prompt).
    object_key = models.CharField(max_length=255, unique=True, editable=False)
    original_filename = models.CharField(max_length=255)  # untrusted, display-only
    display_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)  # server-detected, see storage/backends.py:sniff_mime_type
    size = models.BigIntegerField()
    checksum_sha256 = models.CharField(max_length=64)
    storage_backend = models.CharField(max_length=50, default="s3")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="files_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["bucket", "folder", "display_filename"],
                condition=models.Q(status="active"),
                name="unique_active_filename_per_folder",
            ),
        ]
        indexes = [models.Index(fields=["bucket", "status"])]
        ordering = ["display_filename"]

    def __str__(self):
        return self.display_filename

    @property
    def organization_id(self):
        return self.bucket.project.workspace.organization_id


class FileVersion(models.Model):
    """Append-only version history, populated when a file is overwritten
    in a bucket with versioning enabled (docs/architecture/DATA_MODEL.md
    Section 3.4)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(FileObject, on_delete=models.CASCADE, related_name="versions")
    object_key = models.CharField(max_length=255, unique=True, editable=False)
    size = models.BigIntegerField()
    checksum_sha256 = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="file_versions_created"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.file} @ {self.created_at:%Y-%m-%d %H:%M:%S}"
