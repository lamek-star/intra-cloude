"""Durable portable restore orchestration (not production backup restore).

See docs/operations/RESTORE_IDEMPOTENCY.md for commit windows and recovery.
"""

import hashlib
import logging

from django.db import connections, transaction
from django.utils import timezone
from psycopg import sql

from audit import services as audit
from audit.models import AuditEvent
from databases.models import TenantDatabase
from storage.backends import get_client

from . import restorer
from .crypto import unwrap_passphrase
from .models import RestoreJob
from .preparation import RestorePlan, prepare_restore

logger = logging.getLogger(__name__)


class RestoreReconciliationRequired(Exception):
    """An old job has no trustworthy operation-to-resource mapping."""


def cleanup_completed_source(job: RestoreJob) -> None:
    # Best effort ONLY after durable publication. Duplicate delivery repeats
    # this safe deletion, never the successful restore itself.
    if job.status == RestoreJob.Status.COMPLETED and job.source_object_key:

        def delete_source():
            try:
                get_client().delete(job.source_object_key)
            except Exception as exc:  # noqa: BLE001 - completed result must survive a storage outage
                logger.warning("Restore %s source cleanup pending (%s)", job.id, type(exc).__name__)

        # Also safe when a trusted caller has an enclosing transaction:
        # never delete the only input before the outermost catalog commit.
        transaction.on_commit(delete_source)


def _reconcile_tenant_schemas(plan: RestorePlan, job: RestoreJob) -> None:
    """Rebuild only this operation's unpublished schemas under tenant lock.

    A previous execution may have committed tenant DDL before its control
    connection died. The UUID namespace is server-generated and the source
    package is checksum pinned. No archive-provided identifier is dropped.
    """
    with connections["tenant"].cursor() as cursor:
        # Serializes old tenant transactions even if their control connection
        # was lost. Transaction lock releases on commit/rollback/process loss.
        lock_id = int.from_bytes(job.id.bytes[:8], "big", signed=True)
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [lock_id])
        for database_id in plan.databases.values():
            if TenantDatabase.objects.filter(id=database_id).exists():
                raise RestoreReconciliationRequired("An unpublished restore schema has a catalog owner")
            schema_name = f"db_{database_id.hex}"
            cursor.execute("SELECT 1 FROM pg_namespace WHERE nspname = %s", [schema_name])
            if cursor.fetchone():
                cursor.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema_name)))
                audit.record(
                    actor=job.created_by,
                    organization_id=None,
                    action="import.restore.reconcile",
                    resource_type="restore_job",
                    resource_id=job.id,
                    context={"schema": schema_name},
                )


def _publish(job_id, zf, manifest: dict, plan: RestorePlan) -> RestoreJob:
    with transaction.atomic(using="default"):
        job = RestoreJob.objects.select_for_update().get(id=job_id)
        if job.status == RestoreJob.Status.COMPLETED:
            return job
        if not job.created_by.is_active:
            raise PermissionError("Restore owner is inactive")
        with transaction.atomic(using="tenant"):
            _reconcile_tenant_schemas(plan, job)
            report = restorer.restore_package(zf, manifest, actor=job.created_by, plan=plan)
        # Tenant commits first. A crash here rolls back the catalog; the
        # next execution reconciles the same deterministic tenant schemas.
        job.status = RestoreJob.Status.COMPLETED
        job.organization_id = report.organization_id
        job.report = report.as_dict()
        job.error_message = ""
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "organization", "report", "error_message", "completed_at"])
        audit.record(
            actor=job.created_by,
            organization_id=job.organization_id,
            action="import.restore",
            resource_type="restore_job",
            resource_id=job.id,
            context={"report": job.report},
        )
    return job


def _record_failure(job_id, exc: Exception) -> bool:
    """Return False if another execution already published successfully."""
    with transaction.atomic():
        job = RestoreJob.objects.select_for_update().get(id=job_id)
        if job.status == RestoreJob.Status.COMPLETED:
            return False
        job.status = RestoreJob.Status.FAILED
        # Exception messages can contain restored row/secret values. Keep
        # the failure class and operation identity, never those raw values.
        job.error_message = f"Restore failed ({type(exc).__name__}); source retained for retry/review."
        job.save(update_fields=["status", "error_message"])
        audit.record(
            actor=job.created_by,
            organization_id=None,
            action="import.restore",
            resource_type="restore_job",
            resource_id=job.id,
            result=AuditEvent.Result.ERROR,
            context={"error_type": type(exc).__name__},
        )
    return True


def run_restore(job_id: str, wrapped_passphrase: str | None) -> None:
    job = RestoreJob.objects.get(id=job_id)
    if job.status == RestoreJob.Status.COMPLETED:
        cleanup_completed_source(job)
        return
    try:
        if job.recovery_version != 1 or not job.source_sha256:
            raise RestoreReconciliationRequired("Legacy incomplete job needs operator reconciliation")
        if not job.created_by.is_active:
            raise PermissionError("Restore owner is inactive")
        RestoreJob.objects.filter(id=job.id).exclude(status=RestoreJob.Status.COMPLETED).update(
            status=RestoreJob.Status.VALIDATING
        )
        stream = get_client().get_stream(job.source_object_key)
        try:
            data = stream.read()
        finally:
            stream.close()
        if hashlib.sha256(data).hexdigest() != job.source_sha256:
            raise restorer.PackageValidationError("Staged package differs from original upload")
        zf, manifest = restorer.open_package(data, passphrase=unwrap_passphrase(wrapped_passphrase))
        with zf:
            restorer.verify_checksums(zf, manifest)
            plan = prepare_restore(zf, manifest, job.id)
            RestoreJob.objects.filter(id=job.id).exclude(status=RestoreJob.Status.COMPLETED).update(
                status=RestoreJob.Status.RESTORING
            )
            job = _publish(job.id, zf, manifest, plan)
    except Exception as exc:
        if _record_failure(job.id, exc):
            raise
        job.refresh_from_db()
    cleanup_completed_source(job)
