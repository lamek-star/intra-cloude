"""
Real `pg_dump`/`pg_restore` backup and restore-verification (Phase 11;
docs/operations/BACKUP_RESTORE.md). Restore verification always targets
a throwaway, isolated database on the same server — created immediately
before and dropped immediately after — never production data (Section 6:
"never restore-test against production").
"""

import logging
import os
import subprocess

import psycopg
from django.conf import settings
from django.db import connections
from django.utils import timezone
from psycopg import sql

from .models import BackupRecord

logger = logging.getLogger(__name__)

PG_DUMP_TIMEOUT_SECONDS = 600
PG_RESTORE_TIMEOUT_SECONDS = 600
CONNECT_TIMEOUT_SECONDS = 10

# Django-migration-tracked tables that must exist and be queryable in a
# restored control-plane database — not compared for exact row-count
# equality against the live database, since live data keeps changing
# after the dump is taken; the point is proving the restore is a real,
# structurally intact, queryable database, not a corrupt/empty file.
_CONTROL_DB_VALIDATION_TABLES = (
    "organizations_organization",
    "accounts_user",
    "permissions_permission",
)


class BackupError(Exception):
    pass


def _db_settings(backup_type: str) -> dict:
    # connections[alias].settings_dict, not settings.DATABASES[alias] —
    # under the test runner, Django substitutes the real database name
    # with a "test_"-prefixed one only on the live connection wrapper,
    # not necessarily the raw settings dict (same reasoning as
    # databases/tests/test_connected_databases.py in Phase 8). Using the
    # raw settings dict here would back up/restore-test against the
    # wrong database whenever this runs under pytest.
    alias = "default" if backup_type == BackupRecord.BackupType.CONTROL_DB else "tenant"
    return connections[alias].settings_dict


def _run(cmd: list[str], *, password: str, timeout: int) -> None:
    # PGCONNECT_TIMEOUT bounds how long a bad host/firewall makes this
    # hang trying to connect — independent of `timeout`, which only bounds
    # the whole subprocess (a slow-but-eventually-successful large dump
    # legitimately needs more than a few seconds).
    env = {**os.environ, "PGPASSWORD": password, "PGCONNECT_TIMEOUT": "10"}
    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise BackupError((result.stderr or "").strip()[-2000:] or f"{cmd[0]} exited {result.returncode}")


def run_backup(backup_type: str) -> BackupRecord:
    """Dumps the control-plane or tenant database (custom format — `-Fc`
    — required for `pg_restore`'s selective/parallel restore) to
    `settings.BACKUP_DIR` and records the outcome. Never raises: a
    failure is recorded on the `BackupRecord`, not thrown, so a scheduled
    Celery Beat run never silently dies without a record of what
    happened."""
    db = _db_settings(backup_type)
    record = BackupRecord.objects.create(backup_type=backup_type)

    os.makedirs(settings.BACKUP_DIR, exist_ok=True)
    filename = f"{backup_type}_{record.id.hex}_{timezone.now():%Y%m%dT%H%M%SZ}.dump"
    output_path = os.path.join(settings.BACKUP_DIR, filename)

    cmd = [
        "pg_dump",
        "-h", db["HOST"] or "localhost",
        "-p", str(db["PORT"] or 5432),
        "-U", db["USER"],
        "-d", db["NAME"],
        "-Fc",
        "-f", output_path,
    ]
    try:
        _run(cmd, password=db["PASSWORD"], timeout=PG_DUMP_TIMEOUT_SECONDS)
    except (BackupError, subprocess.TimeoutExpired, OSError) as exc:
        record.status = BackupRecord.Status.FAILED
        record.error_message = str(exc)[:2000]
        record.completed_at = timezone.now()
        record.save(update_fields=["status", "error_message", "completed_at"])
        logger.error("Backup failed for %s: %s", backup_type, exc)
        return record

    record.status = BackupRecord.Status.SUCCESS
    record.file_path = output_path
    record.size_bytes = os.path.getsize(output_path)
    record.completed_at = timezone.now()
    record.save(update_fields=["status", "file_path", "size_bytes", "completed_at"])
    return record


def _admin_connect(db: dict) -> psycopg.Connection:
    # CREATE DATABASE/DROP DATABASE can't run against the database being
    # created/dropped — connect to Postgres's own always-present "postgres"
    # maintenance database instead.
    return psycopg.connect(
        host=db["HOST"] or "localhost",
        port=int(db["PORT"] or 5432),
        dbname="postgres",
        user=db["USER"],
        password=db["PASSWORD"],
        autocommit=True,
        connect_timeout=CONNECT_TIMEOUT_SECONDS,
    )


def _target_connect(db: dict, dbname: str) -> psycopg.Connection:
    return psycopg.connect(
        host=db["HOST"] or "localhost",
        port=int(db["PORT"] or 5432),
        dbname=dbname,
        user=db["USER"],
        password=db["PASSWORD"],
        autocommit=True,
        connect_timeout=CONNECT_TIMEOUT_SECONDS,
    )


def _validate_restored_database(db: dict, test_db_name: str, backup_type: str) -> None:
    with _target_connect(db, test_db_name) as conn, conn.cursor() as cur:
        if backup_type == BackupRecord.BackupType.CONTROL_DB:
            for table in _CONTROL_DB_VALIDATION_TABLES:
                cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table)))
                cur.fetchone()
        else:
            # The tenant database has no Django-migration-tracked tables
            # at all (config/db_routers.py) — only dynamically created
            # per-organization `db_<uuid>` schemas. Proving the schema
            # catalog itself is queryable is the meaningful check here;
            # zero schemas is a valid state (no org created a database
            # yet), so this only ever fails on a genuinely broken restore.
            cur.execute(
                r"SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name LIKE 'db\_%' ESCAPE '\'"
            )
            cur.fetchone()


def verify_backup_restorable(record: BackupRecord) -> BackupRecord:
    """Restores `record` into a freshly created, isolated database on the
    same server, runs a validation pass, then drops the isolated
    database regardless of outcome. Never raises — the result is always
    recorded on `record`."""
    if record.status != BackupRecord.Status.SUCCESS or not record.file_path:
        record.verified_restorable = False
        record.verification_error = "backup did not complete successfully; nothing to verify"
        record.verified_at = timezone.now()
        record.save(update_fields=["verified_restorable", "verification_error", "verified_at"])
        return record

    db = _db_settings(record.backup_type)
    test_db_name = f"restore_test_{record.id.hex[:16]}"

    try:
        with _admin_connect(db) as conn, conn.cursor() as cur:
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(test_db_name)))
    except Exception as exc:  # noqa: BLE001 - always record, never propagate
        record.verified_restorable = False
        record.verification_error = f"could not create restore-test database: {exc}"[:2000]
        record.verified_at = timezone.now()
        record.save(update_fields=["verified_restorable", "verification_error", "verified_at"])
        return record

    try:
        cmd = [
            "pg_restore",
            "-h", db["HOST"] or "localhost",
            "-p", str(db["PORT"] or 5432),
            "-U", db["USER"],
            "-d", test_db_name,
            record.file_path,
        ]
        _run(cmd, password=db["PASSWORD"], timeout=PG_RESTORE_TIMEOUT_SECONDS)
        _validate_restored_database(db, test_db_name, record.backup_type)
    except Exception as exc:  # noqa: BLE001 - always record, never propagate
        record.verified_restorable = False
        record.verification_error = str(exc)[:2000]
    else:
        record.verified_restorable = True
        record.verification_error = ""
    finally:
        try:
            with _admin_connect(db) as conn, conn.cursor() as cur:
                cur.execute(
                    sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(test_db_name))
                )
        except Exception:
            logger.exception("Failed to drop restore-test database %s", test_db_name)

    record.verified_at = timezone.now()
    record.save(update_fields=["verified_restorable", "verification_error", "verified_at"])
    return record
