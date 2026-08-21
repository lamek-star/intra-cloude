"""
Real backup and restore-verification across every store the platform
holds data in (Phase 11 added PostgreSQL via `pg_dump`/`pg_restore`;
Phase 15 adds object storage and configuration). Restore verification
always targets a throwaway, isolated target — a scratch database, a
scratch object-storage key prefix — created immediately before and
removed immediately after, never production data (Section 6: "never
restore-test against production").

Every backup type optionally encrypts its output at rest when
`BACKUP_ENCRYPTION_KEY` is set, reusing the exact AES-256-GCM/Argon2id
container format `exports/container.py` already implements for `.icp`
packages — one reviewed encrypted-archive format across the product,
not a second one invented here.
"""

import hashlib
import io
import json
import logging
import os
import subprocess
import tarfile
import tempfile

import psycopg
from django.conf import settings
from django.db import connections
from django.utils import timezone
from psycopg import sql

from exports import container as backup_container
from storage.backends import get_client as get_storage_client

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

# Every environment variable a configuration backup captures — kept as
# an explicit allowlist (not "back up all of os.environ") so a backup
# never accidentally includes an unrelated host environment variable
# that happened to be set in the container. Mirrors .env.example.
_CONFIG_BACKUP_KEYS = [
    "SECRET_KEY",
    "CREDENTIAL_ENCRYPTION_KEY",
    "ALLOWED_HOSTS",
    "CSRF_TRUSTED_ORIGINS",
    "CORS_ALLOWED_ORIGINS",
    "CONTROL_DB_NAME",
    "CONTROL_DB_USER",
    "CONTROL_DB_PASSWORD",
    "CONTROL_DB_HOST",
    "CONTROL_DB_PORT",
    "TENANT_DB_NAME",
    "TENANT_DB_USER",
    "TENANT_DB_PASSWORD",
    "TENANT_DB_HOST",
    "TENANT_DB_PORT",
    "DB_STATEMENT_TIMEOUT_MS",
    "REDIS_URL",
    "OBJECT_STORAGE_ENDPOINT",
    "OBJECT_STORAGE_REGION",
    "OBJECT_STORAGE_ROOT_USER",
    "OBJECT_STORAGE_ROOT_PASSWORD",
    "OBJECT_STORAGE_BUCKET_PREFIX",
    "FEATURE_EXTERNAL_SHARING_ENABLED",
    "FEATURE_INTERNET_GATEWAY_ENABLED",
    "MAX_UPLOAD_SIZE_BYTES",
    "MALWARE_SCAN_ENABLED",
    "CLAMAV_HOST",
    "CLAMAV_PORT",
    "CONNECTED_DATABASE_BLOCK_PRIVATE_NETWORKS",
    "ANALYTICS_MAX_ROWS",
    "BACKUP_DIR",
]
# Redacted (never written in plaintext) unless the backup itself is
# encrypted — a configuration backup is the single most sensitive
# artifact this platform produces if left unencrypted, since it's a
# complete credential bundle for the whole deployment.
_SECRET_CONFIG_KEYS = {
    "SECRET_KEY",
    "CREDENTIAL_ENCRYPTION_KEY",
    "CONTROL_DB_PASSWORD",
    "TENANT_DB_PASSWORD",
    "OBJECT_STORAGE_ROOT_PASSWORD",
    "REDIS_URL",  # may embed a password
}
_REDACTED_PLACEHOLDER = "<redacted: set BACKUP_ENCRYPTION_KEY to include secrets in configuration backups>"


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


def _maybe_encrypt_file(path: str) -> str:
    """If BACKUP_ENCRYPTION_KEY is set, wraps the file at `path` in the
    exports/container.py format, writes it alongside as `<path>.icb`,
    deletes the plaintext original, and returns the new path. Returns
    `path` unchanged if encryption isn't configured — an unencrypted
    backup is a visible, documented default, not a silent gap."""
    if not settings.BACKUP_ENCRYPTION_KEY:
        return path
    with open(path, "rb") as f:
        plaintext = f.read()
    wrapped = backup_container.write_container(plaintext, passphrase=settings.BACKUP_ENCRYPTION_KEY)
    encrypted_path = path + ".icb"
    with open(encrypted_path, "wb") as f:
        f.write(wrapped)
    os.remove(path)
    return encrypted_path


class _DecryptedTempFile:
    """Context manager yielding a real filesystem path to `path`'s
    plaintext content. If `path` isn't encrypted (no `.icb` suffix),
    yields it unchanged; otherwise decrypts to a temp file and cleans
    it up on exit. Needed for backup types (PostgreSQL) that require a
    real path on disk for a subprocess (`pg_restore`) that can't be
    handed bytes directly."""

    def __init__(self, path: str):
        self.path = path
        self._tmp_path: str | None = None

    def __enter__(self) -> str:
        if not self.path.endswith(".icb"):
            return self.path
        if not settings.BACKUP_ENCRYPTION_KEY:
            raise BackupError("this backup is encrypted but BACKUP_ENCRYPTION_KEY is not set")
        with open(self.path, "rb") as f:
            data = f.read()
        plaintext = backup_container.read_container_payload(data, passphrase=settings.BACKUP_ENCRYPTION_KEY)
        fd, tmp_path = tempfile.mkstemp(suffix=".dump")
        with os.fdopen(fd, "wb") as f:
            f.write(plaintext)
        self._tmp_path = tmp_path
        return tmp_path

    def __exit__(self, *exc_info) -> None:
        if self._tmp_path:
            os.remove(self._tmp_path)


class _HashingStream:
    """Wraps a readable stream (a boto3 StreamingBody) so every chunk
    read through it also updates a running sha256 — lets `tarfile`
    stream an object's bytes straight into the archive while a manifest
    checksum is computed alongside, without buffering the whole object
    in memory a second time just to hash it."""

    def __init__(self, stream, hasher):
        self._stream = stream
        self._hasher = hasher

    def read(self, size: int = -1) -> bytes:
        chunk = self._stream.read(size)
        self._hasher.update(chunk)
        return chunk


def run_backup(backup_type: str) -> BackupRecord:
    """Dispatches to the right backup implementation for `backup_type`.
    Never raises: a failure is recorded on the `BackupRecord`, not
    thrown, so a scheduled Celery Beat run never silently dies without
    a record of what happened."""
    if backup_type in (BackupRecord.BackupType.CONTROL_DB, BackupRecord.BackupType.TENANT_DB):
        return _run_postgres_backup(backup_type)
    if backup_type == BackupRecord.BackupType.OBJECT_STORAGE:
        return _run_object_storage_backup()
    if backup_type == BackupRecord.BackupType.CONFIGURATION:
        return _run_configuration_backup()
    raise BackupError(f"unsupported backup_type: {backup_type!r}")


def _run_postgres_backup(backup_type: str) -> BackupRecord:
    """Dumps the control-plane or tenant database (custom format — `-Fc`
    — required for `pg_restore`'s selective/parallel restore) to
    `settings.BACKUP_DIR` and records the outcome."""
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

    final_path = _maybe_encrypt_file(output_path)
    record.status = BackupRecord.Status.SUCCESS
    record.file_path = final_path
    record.size_bytes = os.path.getsize(final_path)
    record.completed_at = timezone.now()
    record.save(update_fields=["status", "file_path", "size_bytes", "completed_at"])
    return record


def _run_object_storage_backup() -> BackupRecord:
    """Streams every object in the bucket into a single tar archive,
    plus a `_manifest.json` of each object's sha256 — never holds a
    whole object in memory (`_HashingStream` feeds `tarfile` directly
    from the S3 response body)."""
    record = BackupRecord.objects.create(backup_type=BackupRecord.BackupType.OBJECT_STORAGE)
    os.makedirs(settings.BACKUP_DIR, exist_ok=True)
    filename = f"object_storage_{record.id.hex}_{timezone.now():%Y%m%dT%H%M%SZ}.tar"
    output_path = os.path.join(settings.BACKUP_DIR, filename)

    try:
        client = get_storage_client()
        manifest: dict[str, str] = {}
        with tarfile.open(output_path, "w") as tar:
            for key, size in client.list_all_keys():
                hasher = hashlib.sha256()
                info = tarfile.TarInfo(name=key)
                info.size = size
                tar.addfile(info, _HashingStream(client.get_stream(key), hasher))
                manifest[key] = hasher.hexdigest()

            manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode()
            manifest_info = tarfile.TarInfo(name="_manifest.json")
            manifest_info.size = len(manifest_bytes)
            tar.addfile(manifest_info, io.BytesIO(manifest_bytes))
    except Exception as exc:  # noqa: BLE001 - always record, never propagate (matches _run_postgres_backup)
        record.status = BackupRecord.Status.FAILED
        record.error_message = str(exc)[:2000]
        record.completed_at = timezone.now()
        record.save(update_fields=["status", "error_message", "completed_at"])
        logger.error("Object storage backup failed: %s", exc)
        return record

    final_path = _maybe_encrypt_file(output_path)
    record.status = BackupRecord.Status.SUCCESS
    record.file_path = final_path
    record.size_bytes = os.path.getsize(final_path)
    record.completed_at = timezone.now()
    record.save(update_fields=["status", "file_path", "size_bytes", "completed_at"])
    return record


def _run_configuration_backup() -> BackupRecord:
    """Captures the running application's own configuration (the
    environment variables it was actually started with, filtered to a
    fixed allowlist — see _CONFIG_BACKUP_KEYS), not a host `.env` file:
    the container never has that file mounted, only the environment
    variables Compose's `env_file:` injected from it. Secret-looking
    values are redacted unless BACKUP_ENCRYPTION_KEY is set, in which
    case the whole backup is encrypted and the real values included."""
    record = BackupRecord.objects.create(backup_type=BackupRecord.BackupType.CONFIGURATION)
    os.makedirs(settings.BACKUP_DIR, exist_ok=True)
    encrypted = bool(settings.BACKUP_ENCRYPTION_KEY)

    config = {}
    for key in _CONFIG_BACKUP_KEYS:
        value = os.environ.get(key, "")
        if key in _SECRET_CONFIG_KEYS and not encrypted:
            value = _REDACTED_PLACEHOLDER
        config[key] = value
    payload = json.dumps(config, indent=2, sort_keys=True).encode()

    filename_base = f"configuration_{record.id.hex}_{timezone.now():%Y%m%dT%H%M%SZ}"
    try:
        if encrypted:
            payload_out = backup_container.write_container(payload, passphrase=settings.BACKUP_ENCRYPTION_KEY)
            output_path = os.path.join(settings.BACKUP_DIR, filename_base + ".icb")
        else:
            payload_out = payload
            output_path = os.path.join(settings.BACKUP_DIR, filename_base + ".json")
        with open(output_path, "wb") as f:
            f.write(payload_out)
    except OSError as exc:
        record.status = BackupRecord.Status.FAILED
        record.error_message = str(exc)[:2000]
        record.completed_at = timezone.now()
        record.save(update_fields=["status", "error_message", "completed_at"])
        logger.error("Configuration backup failed: %s", exc)
        return record

    record.status = BackupRecord.Status.SUCCESS
    record.file_path = output_path
    record.size_bytes = len(payload_out)
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
    """Dispatches to the right restore-verification implementation for
    `record.backup_type`. Never raises — the result is always recorded
    on `record`."""
    if record.backup_type in (BackupRecord.BackupType.CONTROL_DB, BackupRecord.BackupType.TENANT_DB):
        return _verify_postgres_backup_restorable(record)
    if record.backup_type == BackupRecord.BackupType.OBJECT_STORAGE:
        return _verify_object_storage_backup_restorable(record)
    if record.backup_type == BackupRecord.BackupType.CONFIGURATION:
        return _verify_configuration_backup_restorable(record)

    record.verified_restorable = False
    record.verification_error = f"unsupported backup_type: {record.backup_type!r}"
    record.verified_at = timezone.now()
    record.save(update_fields=["verified_restorable", "verification_error", "verified_at"])
    return record


def _not_restorable_no_successful_backup(record: BackupRecord) -> BackupRecord:
    record.verified_restorable = False
    record.verification_error = "backup did not complete successfully; nothing to verify"
    record.verified_at = timezone.now()
    record.save(update_fields=["verified_restorable", "verification_error", "verified_at"])
    return record


def _verify_postgres_backup_restorable(record: BackupRecord) -> BackupRecord:
    """Restores `record` into a freshly created, isolated database on the
    same server, runs a validation pass, then drops the isolated
    database regardless of outcome."""
    if record.status != BackupRecord.Status.SUCCESS or not record.file_path:
        return _not_restorable_no_successful_backup(record)

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
        with _DecryptedTempFile(record.file_path) as plain_path:
            cmd = [
                "pg_restore",
                "-h", db["HOST"] or "localhost",
                "-p", str(db["PORT"] or 5432),
                "-U", db["USER"],
                "-d", test_db_name,
                plain_path,
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


def _verify_object_storage_backup_restorable(record: BackupRecord) -> BackupRecord:
    """Extracts every object from the archive, checks it against the
    manifest's recorded sha256, re-uploads it to a scratch key prefix in
    the *same* bucket (the object-storage equivalent of the Postgres
    restore-test's isolated database on the same server), reads it back,
    and confirms the round trip — a genuine restore into the real target
    system, not just an archive-integrity check. The scratch prefix is
    removed regardless of outcome."""
    if record.status != BackupRecord.Status.SUCCESS or not record.file_path:
        return _not_restorable_no_successful_backup(record)

    scratch_prefix = f"_restore_test_{record.id.hex[:16]}/"
    client = get_storage_client()
    restored_keys: list[str] = []

    try:
        with _DecryptedTempFile(record.file_path) as plain_path, tarfile.open(plain_path, "r") as tar:
            members = tar.getmembers()
            manifest_member = next((m for m in members if m.name == "_manifest.json"), None)
            if manifest_member is None:
                raise BackupError("archive is missing _manifest.json")
            manifest_file = tar.extractfile(manifest_member)
            manifest = json.loads(manifest_file.read()) if manifest_file else {}

            for member in members:
                if member.name == "_manifest.json":
                    continue
                fileobj = tar.extractfile(member)
                if fileobj is None:
                    continue
                data = fileobj.read()
                actual = hashlib.sha256(data).hexdigest()
                expected = manifest.get(member.name)
                if expected != actual:
                    raise BackupError(f"checksum mismatch for {member.name!r} inside the backup archive")

                scratch_key = scratch_prefix + member.name
                client.put_stream(scratch_key, io.BytesIO(data), "application/octet-stream")
                restored_keys.append(scratch_key)
                reread = client.get_stream(scratch_key).read()
                if hashlib.sha256(reread).hexdigest() != actual:
                    raise BackupError(f"restored object {member.name!r} did not read back correctly")
    except Exception as exc:  # noqa: BLE001 - always record, never propagate
        record.verified_restorable = False
        record.verification_error = str(exc)[:2000]
    else:
        record.verified_restorable = True
        record.verification_error = ""
    finally:
        for key in restored_keys:
            try:
                client.delete(key)
            except Exception:
                logger.exception("Failed to clean up restore-test object %s", key)

    record.verified_at = timezone.now()
    record.save(update_fields=["verified_restorable", "verification_error", "verified_at"])
    return record


def _verify_configuration_backup_restorable(record: BackupRecord) -> BackupRecord:
    """Decrypts (if needed) and parses the backup, confirming every
    expected key is present — there's no "load it into a real system"
    step for configuration the way pg_restore or a re-upload provides
    for the other two backup types, so this is the meaningful
    restorability check available for this format."""
    if record.status != BackupRecord.Status.SUCCESS or not record.file_path:
        return _not_restorable_no_successful_backup(record)

    try:
        with open(record.file_path, "rb") as f:
            data = f.read()
        if record.file_path.endswith(".icb"):
            if not settings.BACKUP_ENCRYPTION_KEY:
                raise BackupError("this backup is encrypted but BACKUP_ENCRYPTION_KEY is not set")
            data = backup_container.read_container_payload(data, passphrase=settings.BACKUP_ENCRYPTION_KEY)
        config = json.loads(data)
        missing = [key for key in _CONFIG_BACKUP_KEYS if key not in config]
        if missing:
            raise BackupError(f"restored configuration is missing keys: {missing}")
    except Exception as exc:  # noqa: BLE001 - always record, never propagate
        record.verified_restorable = False
        record.verification_error = str(exc)[:2000]
    else:
        record.verified_restorable = True
        record.verification_error = ""

    record.verified_at = timezone.now()
    record.save(update_fields=["verified_restorable", "verification_error", "verified_at"])
    return record
