"""Read-only inspection of a backup set before it is restored (the guided restore's Validate / Preview /
Compatibility steps). Never connects to or changes a live database.

For each of the three files (control database, tenant database, object storage):
  - it exists, its size and SHA-256;
  - encrypted backups are decrypted to a temporary file (which proves the key is right and the data
    unchanged: the container is authenticated);
  - database dumps must be readable archives (`pg_restore --list`);
  - every stored object is re-hashed against the backup's own manifest.
From the control database dump it reads which migrations were applied (compared with this program's
migrations: a backup made by a NEWER program cannot be restored into this one) and which applications were
installed; from the tenant dump, which application schemas it holds and a few of their row counts.
"""

import csv
import hashlib
import io
import json
import os
import re
import subprocess
import tarfile

from django.db.migrations.loader import MigrationLoader

from exports.container import ContainerError

from .backups import BackupError, _DecryptedTempFile

PG_TIMEOUT_SECONDS = 600
# A wrong key or a changed byte (ContainerError: the encryption is authenticated), an unreadable
# archive, a hung tool.
UNREADABLE = (BackupError, ContainerError, OSError, ValueError, subprocess.TimeoutExpired)
COUNTED_TABLES = ("products", "customers", "invoices", "catalogue_parts", "stock_movements", "files")


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _pg_restore(*args: str) -> str:
    result = subprocess.run(["pg_restore", *args], capture_output=True, text=True, timeout=PG_TIMEOUT_SECONDS)
    if result.returncode != 0:
        raise BackupError((result.stderr or "").strip()[-500:] or "pg_restore could not read the archive")
    return result.stdout


def _copy_rows(dump: str, table: str, schema: str = "public") -> list[dict]:
    """The rows of one table from a dump's data section (COPY text format), as dicts."""
    out = _pg_restore("--data-only", "--schema", schema, "--table", table, "-f", "-", dump)
    rows: list[dict] = []
    columns: list[str] | None = None
    for line in out.splitlines():
        m = re.match(r"^COPY \S+ \((.*)\) FROM stdin;$", line)
        if m:
            columns = [c.strip().strip('"') for c in m.group(1).split(",")]
            continue
        if columns is None:
            continue
        if line == "\\.":
            break
        values = next(csv.reader(io.StringIO(line), delimiter="\t", quoting=csv.QUOTE_NONE))
        rows.append({c: (None if v == "\\N" else v) for c, v in zip(columns, values, strict=False)})
    return rows


def _count_rows(dump: str, schema: str, table: str) -> int:
    out = _pg_restore("--data-only", "--schema", schema, "--table", table, "-f", "-", dump)
    inside, n = False, 0
    for line in out.splitlines():
        if line.startswith("COPY "):
            inside = True
            continue
        if inside:
            if line == "\\.":
                break
            n += 1
    return n


def inspect_backup_set(control: str, tenant: str, objects: str) -> dict:
    report: dict = {
        "ok": True,
        "errors": [],
        "warnings": [],
        "files": {},
        "applications": [],
        "compatible": True,
    }

    def fail(message: str):
        report["ok"] = False
        report["errors"].append(message)

    for kind, path in (("control_db", control), ("tenant_db", tenant), ("object_storage", objects)):
        if not path or not os.path.isfile(path):
            fail(f"The {kind} backup file is missing.")
            continue
        report["files"][kind] = {
            "name": os.path.basename(path),
            "bytes": os.path.getsize(path),
            "sha256": _sha256(path),
            "encrypted": path.endswith(".icb"),
        }
    if not report["ok"]:
        return report

    # ---- control database: readable, migration level, installed applications
    try:
        with _DecryptedTempFile(control) as dump:
            _pg_restore("--list", dump)
            applied = {(r["app"], r["name"]) for r in _copy_rows(dump, "django_migrations")}
            try:
                apps = _copy_rows(dump, "service_apps_serviceapp")
            except BackupError:
                apps = []  # made before service applications existed
        loader = MigrationLoader(None, ignore_no_migrations=True)
        known = set(loader.disk_migrations.keys())
        newer = sorted(f"{a}.{n}" for a, n in applied - known)
        missing = len(known - applied)
        report["migrations"] = {
            "in_backup": len(applied),
            "in_program": len(known),
            "program_newer_by": missing,
        }
        if newer:
            report["compatible"] = False
            fail(
                "This backup was made by a NEWER IntraForge than the one installed (it contains changes this "
                f"version does not know: {', '.join(newer[:5])}{'...' if len(newer) > 5 else ''}). "
                "Install that version first."
            )
        elif missing:
            report["warnings"].append(
                f"The backup is from an older IntraForge ({missing} later database change(s) are applied "
                "after restoring)."
            )
        for a in apps:
            report["applications"].append(
                {
                    "display_name": a.get("display_name"),
                    "app_type": a.get("app_type"),
                    "schema": a.get("schema_name"),
                    "removed": a.get("removed_at") not in (None, ""),
                }
            )
        report["files"]["control_db"]["valid"] = True
    except UNREADABLE as exc:
        fail(f"The control database backup cannot be read: {exc}")
        return report

    # ---- tenant database: readable, the applications' data
    try:
        with _DecryptedTempFile(tenant) as dump:
            listing = _pg_restore("--list", dump)
            schemas = set(re.findall(r"\bSCHEMA - (\S+)", listing))
            for app in report["applications"]:
                schema = app["schema"]
                app["data_present"] = schema in schemas
                if schema in schemas:
                    app["counts"] = {
                        t: _count_rows(dump, schema, t)
                        for t in COUNTED_TABLES
                        if f"TABLE DATA {schema} {t} " in listing
                    }
        report["files"]["tenant_db"]["valid"] = True
        for app in report["applications"]:
            if not app.get("data_present") and not app["removed"]:
                report["warnings"].append(f"{app['display_name']}: its data is not in the tenant backup.")
    except UNREADABLE as exc:
        fail(f"The business data backup cannot be read: {exc}")
        return report

    # ---- object storage: every object re-hashed against the manifest
    try:
        with _DecryptedTempFile(objects) as archive, tarfile.open(archive, "r") as tar:
            manifest = None
            hashes: dict[str, str] = {}
            total = 0
            for member in tar:
                if not member.isfile():
                    continue
                data = tar.extractfile(member)
                if data is None:
                    continue
                if member.name == "_manifest.json":
                    manifest = json.loads(data.read())
                    continue
                h = hashlib.sha256()
                while chunk := data.read(1 << 20):
                    h.update(chunk)
                hashes[member.name] = h.hexdigest()
                total += member.size
            if manifest is None:
                raise BackupError("the archive has no manifest")
            bad = [k for k, v in manifest.items() if hashes.get(k) != v]
            if bad:
                raise BackupError(f"{len(bad)} stored file(s) do not match their checksum")
            report["objects"] = {"count": len(hashes), "bytes": total, "verified": len(manifest)}
        report["files"]["object_storage"]["valid"] = True
    except (*UNREADABLE, tarfile.TarError) as exc:
        fail(f"The stored-files backup cannot be read: {exc}")
    return report
