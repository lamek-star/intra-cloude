"""
Orchestration for export/restore jobs: permission checks, audit events,
and moving the .icp package's bytes to/from object storage — kept
separate from builder.py/restorer.py, which know nothing about jobs,
permissions, or storage keys and are reusable on their own.
"""

import uuid

from django.conf import settings
from django.http import Http404

from audit import services as audit
from audit.models import AuditEvent
from organizations.models import Membership, Organization
from permissions.services import has_permission
from storage.backends import get_client

from . import builder, restorer
from .crypto import unwrap_passphrase, wrap_passphrase
from .models import ExportJob, RestoreJob

EXPORT_STORAGE_PREFIX = "exports"
RESTORE_STAGING_PREFIX = "restore-staging"


class ExportPermissionDenied(Exception):
    pass


class RestoreValidationError(Exception):
    pass


def get_member_export_job(user, job_id) -> ExportJob:
    try:
        return ExportJob.objects.select_related("organization").get(
            id=job_id,
            organization__memberships__user=user,
            organization__memberships__status=Membership.Status.ACTIVE,
        )
    except ExportJob.DoesNotExist as exc:
        raise Http404 from exc


def start_export(*, actor, organization: Organization, passphrase: str | None = None) -> ExportJob:
    if not has_permission(actor, "export.manage", organization_id=organization.id):
        audit.record(
            actor=actor,
            organization_id=organization.id,
            action="export.create",
            resource_type="organization",
            resource_id=organization.id,
            result=AuditEvent.Result.DENIED,
        )
        raise ExportPermissionDenied("export.manage required")

    job = ExportJob.objects.create(
        organization=organization, created_by=actor, encrypted=passphrase is not None
    )

    from .tasks import run_export_task

    run_export_task.delay(str(job.id), wrap_passphrase(passphrase))
    return job


def run_export(job_id: str, wrapped_passphrase: str | None) -> None:
    passphrase = unwrap_passphrase(wrapped_passphrase)
    job = ExportJob.objects.select_related("organization").get(id=job_id)
    job.status = ExportJob.Status.RUNNING
    job.save(update_fields=["status"])

    try:
        container_bytes, checksum = builder.build_export(organization=job.organization, passphrase=passphrase)
    except Exception as exc:
        job.status = ExportJob.Status.FAILED
        job.error_message = str(exc)[:2000]
        job.save(update_fields=["status", "error_message"])
        audit.record(
            actor=job.created_by,
            organization_id=job.organization_id,
            action="export.create",
            resource_type="export_job",
            resource_id=job.id,
            result=AuditEvent.Result.ERROR,
        )
        raise

    object_key = f"{EXPORT_STORAGE_PREFIX}/{job.organization_id}/{job.id}.icp"
    client = get_client()
    client.put_stream(object_key, _BytesReader(container_bytes), "application/octet-stream")

    from django.utils import timezone

    job.status = ExportJob.Status.COMPLETED
    job.object_key = object_key
    job.size_bytes = len(container_bytes)
    job.checksum_sha256 = checksum
    job.completed_at = timezone.now()
    job.save(update_fields=["status", "object_key", "size_bytes", "checksum_sha256", "completed_at"])

    audit.record(
        actor=job.created_by,
        organization_id=job.organization_id,
        action="export.create",
        resource_type="export_job",
        resource_id=job.id,
        context={"size_bytes": job.size_bytes, "encrypted": job.encrypted},
    )


def download_export(*, actor, job: ExportJob):
    if not has_permission(actor, "export.manage", organization_id=job.organization_id):
        raise ExportPermissionDenied("export.manage required")
    if job.status != ExportJob.Status.COMPLETED:
        raise RestoreValidationError("export is not complete")
    audit.record(
        actor=actor,
        organization_id=job.organization_id,
        action="export.download",
        resource_type="export_job",
        resource_id=job.id,
    )
    return get_client().get_stream(job.object_key)


def stage_restore_upload(*, actor, uploaded_file, passphrase: str | None = None) -> RestoreJob:
    """Stores the uploaded .icp bytes in object storage and creates the
    RestoreJob row. Permission is deliberately NOT checked against any
    organization here — restoring creates a *new* one, so there is
    nothing yet to scope a permission check to; any authenticated user
    may attempt a restore (they become that new organization's
    administrator, exactly like anyone creating a brand-new
    organization normally would)."""
    data = uploaded_file.read()
    if len(data) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise RestoreValidationError(
            f"package exceeds the maximum upload size of {settings.MAX_UPLOAD_SIZE_BYTES} bytes"
        )

    job = RestoreJob.objects.create(created_by=actor, source_object_key="")
    object_key = f"{RESTORE_STAGING_PREFIX}/{job.id}.icp"
    get_client().put_stream(object_key, _BytesReader(data), "application/octet-stream")
    job.source_object_key = object_key
    job.save(update_fields=["source_object_key"])

    from .tasks import run_restore_task

    run_restore_task.delay(str(job.id), wrap_passphrase(passphrase))
    return job


def run_restore(job_id: str, wrapped_passphrase: str | None) -> None:
    from django.utils import timezone

    passphrase = unwrap_passphrase(wrapped_passphrase)

    job = RestoreJob.objects.get(id=job_id)
    job.status = RestoreJob.Status.VALIDATING
    job.save(update_fields=["status"])

    client = get_client()
    container_bytes = client.get_stream(job.source_object_key).read()

    try:
        zf, manifest = restorer.open_package(container_bytes, passphrase=passphrase)
        restorer.verify_checksums(zf, manifest)

        job.status = RestoreJob.Status.RESTORING
        job.save(update_fields=["status"])

        report = restorer.restore_package(zf, manifest, actor=job.created_by)
    except Exception as exc:
        job.status = RestoreJob.Status.FAILED
        job.error_message = str(exc)[:2000]
        job.save(update_fields=["status", "error_message"])
        audit.record(
            actor=job.created_by,
            organization_id=None,
            action="import.restore",
            resource_type="restore_job",
            resource_id=job.id,
            result=AuditEvent.Result.ERROR,
            context={"error": str(exc)[:500]},
        )
        raise
    finally:
        try:
            client.delete(job.source_object_key)
        except Exception:  # noqa: BLE001 - staging cleanup must never mask the real result
            pass

    job.status = RestoreJob.Status.COMPLETED
    job.organization_id = uuid.UUID(report.organization_id)
    job.report = report.as_dict()
    job.completed_at = timezone.now()
    job.save(update_fields=["status", "organization", "report", "completed_at"])

    audit.record(
        actor=job.created_by,
        organization_id=job.organization_id,
        action="import.restore",
        resource_type="restore_job",
        resource_id=job.id,
        context={"report": job.report},
    )


class _BytesReader:
    """Minimal file-like wrapper so raw bytes can go through
    ObjectStorageClient.put_stream (which expects a file object with
    .read(), for boto3's upload_fileobj)."""

    def __init__(self, data: bytes):
        self._buf = data
        self._pos = 0

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            chunk = self._buf[self._pos :]
            self._pos = len(self._buf)
            return chunk
        chunk = self._buf[self._pos : self._pos + size]
        self._pos += len(chunk)
        return chunk
