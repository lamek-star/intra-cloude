"""
The CSV import pipeline's execution layer. `start_import` (called from the
view, synchronous, cheap) validates and creates the `ImportJob`, then
enqueues the actual work. `run_import` (called from the Celery task) does
the real streamed, chunked bulk insert against the tenant connection.

Encoding/delimiter are never re-sniffed here — a streamed S3 body can't be
rewound, so the values confirmed at preview time (`imports/inspect.py`)
are trusted as-is (`ImportJob.encoding`/`delimiter`).
"""

import csv
import logging
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db import connections, transaction
from django.http import Http404
from django.utils import timezone
from psycopg import sql

from databases.formats import BOOLEAN_FALSE_VALUES, BOOLEAN_TRUE_VALUES, DATE_FORMAT, DATETIME_FORMATS
from databases.models import DBColumn, DBTable
from organizations.models import Membership
from permissions.services import has_permission
from storage.backends import get_client
from storage.models import FileObject

from .models import ImportJob, ImportJobError

logger = logging.getLogger(__name__)

CHUNK_ROWS = 1000
MAX_STORED_ERRORS = 1000
# Column every table gets automatically (Phase 4) — never a valid CSV
# import target, Postgres generates it.
_RESERVED_TARGET_COLUMNS = {"id"}


class ImportValidationError(Exception):
    pass


class ImportPermissionDenied(Exception):
    pass


def get_member_import_job(user, job_id) -> ImportJob:
    try:
        return ImportJob.objects.select_related(
            "table__tenant_database__project__workspace__organization"
        ).get(
            id=job_id,
            table__tenant_database__project__workspace__organization__memberships__user=user,
            table__tenant_database__project__workspace__organization__memberships__status=Membership.Status.ACTIVE,
        )
    except ImportJob.DoesNotExist as exc:
        raise Http404 from exc


def validate_column_mapping(table: DBTable, column_mapping: list[dict]) -> None:
    if not column_mapping:
        raise ImportValidationError("column_mapping must not be empty")

    columns_by_name = {c.name: c for c in table.columns.all()}
    seen_targets = set()
    for entry in column_mapping:
        target = entry.get("target_column")
        target_type = entry.get("target_type")
        if not entry.get("csv_column") or not target or not target_type:
            raise ImportValidationError(
                "each column_mapping entry needs csv_column, target_column, and target_type"
            )
        if target in _RESERVED_TARGET_COLUMNS:
            raise ImportValidationError(f"{target!r} is generated automatically and can't be imported into")
        if target in seen_targets:
            raise ImportValidationError(f"target_column {target!r} is mapped more than once")
        seen_targets.add(target)
        column = columns_by_name.get(target)
        if column is None:
            raise ImportValidationError(f"table has no column named {target!r}")
        if column.data_type != target_type:
            raise ImportValidationError(
                f"target_type {target_type!r} for {target!r} doesn't match the column's actual "
                f"type {column.data_type!r}"
            )


def start_import(
    *,
    actor,
    table: DBTable,
    file: FileObject,
    encoding: str,
    delimiter: str,
    column_mapping: list[dict],
) -> ImportJob:
    org_id = table.organization_id
    if not has_permission(actor, "dataset.import", organization_id=org_id):
        raise ImportPermissionDenied("dataset.import required")

    validate_column_mapping(table, column_mapping)

    job = ImportJob.objects.create(
        file=file,
        table=table,
        encoding=encoding,
        delimiter=delimiter,
        column_mapping=column_mapping,
        created_by=actor,
    )

    from .tasks import run_import_task

    run_import_task.delay(str(job.id))
    return job


def _convert_value(raw: str, data_type: str):
    raw = raw.strip()
    if raw == "":
        return None
    if data_type in (DBColumn.DataType.INTEGER, DBColumn.DataType.BIGINT):
        return int(raw)
    if data_type == DBColumn.DataType.DECIMAL:
        try:
            return Decimal(raw)
        except InvalidOperation as exc:
            raise ValueError(f"not a valid decimal: {raw!r}") from exc
    if data_type == DBColumn.DataType.BOOLEAN:
        lowered = raw.lower()
        if lowered in BOOLEAN_TRUE_VALUES:
            return True
        if lowered in BOOLEAN_FALSE_VALUES:
            return False
        raise ValueError(f"not a valid boolean: {raw!r}")
    if data_type == DBColumn.DataType.DATE:
        return datetime.strptime(raw, DATE_FORMAT).date()
    if data_type == DBColumn.DataType.DATETIME:
        for fmt in DATETIME_FORMATS:
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
        raise ValueError(f"not a valid datetime: {raw!r}")
    if data_type == DBColumn.DataType.UUID:
        return str(uuid.UUID(raw))
    if data_type == DBColumn.DataType.JSON:
        import json

        return json.loads(raw)
    return raw  # text / varchar


def _decoded_lines(body, encoding: str):
    for line_bytes in body.iter_lines():
        yield line_bytes.decode(encoding, errors="replace")


def run_import(job_id: str) -> None:
    job = ImportJob.objects.select_related("table__tenant_database", "file").get(id=job_id)
    job.status = ImportJob.Status.RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])

    table = job.table
    mapping = job.column_mapping
    target_columns = [m["target_column"] for m in mapping]

    insert_sql = sql.SQL("INSERT INTO {schema}.{table} ({cols}) VALUES ({placeholders})").format(
        schema=sql.Identifier(table.tenant_database.schema_name),
        table=sql.Identifier(table.name),
        cols=sql.SQL(", ").join(sql.Identifier(c) for c in target_columns),
        placeholders=sql.SQL(", ").join(sql.Placeholder() for _ in target_columns),
    )

    body = get_client().get_stream(job.file.object_key)
    reader = csv.DictReader(_decoded_lines(body, job.encoding), delimiter=job.delimiter)

    imported = job.imported_rows
    rejected = job.rejected_rows
    row_number = job.last_processed_row
    pending_errors: list[ImportJobError] = []

    try:
        with connections["tenant"].cursor() as cursor:
            for row_number, row in enumerate(reader, start=1):
                if row_number <= job.last_processed_row:
                    continue  # resuming a retried job — already committed

                try:
                    values = [_convert_value(row.get(m["csv_column"], ""), m["target_type"]) for m in mapping]
                    with transaction.atomic(using="tenant"):
                        cursor.execute(insert_sql, values)
                    imported += 1
                except Exception as exc:  # noqa: BLE001 - any bad row is rejected, not fatal to the job
                    rejected += 1
                    if len(pending_errors) < MAX_STORED_ERRORS:
                        pending_errors.append(
                            ImportJobError(
                                job=job, row_number=row_number, message=str(exc)[:500], raw_row=row
                            )
                        )

                if row_number % CHUNK_ROWS == 0:
                    _checkpoint(job, imported, rejected, row_number, pending_errors)
                    pending_errors = []
    except Exception as exc:
        _checkpoint(job, imported, rejected, row_number, pending_errors)
        job.status = ImportJob.Status.FAILED
        job.error_message = str(exc)[:2000]
        job.save(update_fields=["status", "error_message"])
        logger.exception("Import job %s failed", job_id)
        return

    _checkpoint(job, imported, rejected, row_number, pending_errors)
    job.total_rows = row_number
    job.status = ImportJob.Status.COMPLETED
    job.completed_at = timezone.now()
    job.save(update_fields=["total_rows", "status", "completed_at"])


def _checkpoint(job: ImportJob, imported: int, rejected: int, row_number: int, pending_errors: list) -> None:
    job.imported_rows = imported
    job.rejected_rows = rejected
    job.last_processed_row = row_number
    job.save(update_fields=["imported_rows", "rejected_rows", "last_processed_row"])
    if pending_errors:
        ImportJobError.objects.bulk_create(pending_errors)
