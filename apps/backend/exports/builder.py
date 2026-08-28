"""
Builds a .icp package for one Organization: its workspace/project tree,
tenant databases (schema + row data), object storage (bucket/folder/file
structure + real file bytes), and membership/role-assignment metadata.

Deliberately excluded from this first implementation — see
manifest.EXCLUDED_SCOPE, recorded in every manifest rather than silently
dropped: applications/service-account credentials, sharing grants,
connected-database definitions, analytics (none exist yet), and user
password hashes (opt-in only).

The archive is built to a temporary file (never fully in memory during
construction — files can be large) and only read back into memory once,
for the optional encryption pass and outer-container wrapping — a real
but currently-accepted bound on export size, matching the "generous but
real" bound style already used elsewhere in this codebase (e.g.
DB_STATEMENT_TIMEOUT_MS). Streaming/chunked encryption is a future
improvement, not implemented here.
"""

import csv
import hashlib
import io
import tempfile
import uuid
import zipfile

from databases.models import DBForeignKey
from databases.rows import iter_export_rows
from organizations.models import Membership
from permissions.catalog import SYSTEM_ROLES
from permissions.models import RoleAssignment
from storage.backends import get_client
from storage.models import FileObject

from . import container
from .manifest import new_manifest


def _column_dict(column) -> dict:
    return {
        "name": column.name,
        "data_type": column.data_type,
        "max_length": column.max_length,
        "precision": column.precision,
        "scale": column.scale,
        "is_nullable": column.is_nullable,
        "is_unique": column.is_unique,
        "default_value": column.default_value,
    }


def _folder_path(folder) -> list[str]:
    path = []
    while folder is not None:
        path.append(folder.name)
        folder = folder.parent
    return list(reversed(path))


class _ArchiveWriter:
    """Thin wrapper around ZipFile that tracks a sha256 checksum for
    every entry as it's written, feeding manifest["checksums"] — package
    integrity is verified per-file on restore, not just trusted from
    ZIP's own (non-cryptographic) CRC32."""

    def __init__(self, zf: zipfile.ZipFile, checksums: dict):
        self._zf = zf
        self._checksums = checksums

    def write_bytes(self, arcname: str, data: bytes) -> None:
        self._checksums[arcname] = hashlib.sha256(data).hexdigest()
        self._zf.writestr(arcname, data)

    def write_stream(self, arcname: str, chunks) -> str:
        """Streams `chunks` (an iterable of bytes) into the archive
        without materializing the whole object in memory — used for
        file objects, which can be large. Returns the sha256 hex digest."""
        hasher = hashlib.sha256()
        with self._zf.open(arcname, "w") as entry:
            for chunk in chunks:
                hasher.update(chunk)
                entry.write(chunk)
        digest = hasher.hexdigest()
        self._checksums[arcname] = digest
        return digest


def build_export(*, organization, passphrase: str | None = None) -> tuple[bytes, str]:
    """Returns (container_bytes, checksum_sha256_of_container). Reads
    real tenant Postgres data and real object storage bytes — nothing
    here is mocked or simulated."""
    export_id = str(uuid.uuid4())
    manifest = new_manifest(export_id=export_id)

    workspaces_payload = []
    databases_manifest: dict = {}
    content_hash_to_arcname: dict[str, str] = {}  # de-duplicates identical file bytes

    with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
            writer = _ArchiveWriter(zf, manifest["checksums"])

            for workspace in organization.workspaces.order_by("name"):
                projects_payload = []
                for project in workspace.projects.order_by("name"):
                    db_refs = []
                    for tenant_db in project.tenant_databases.order_by("name"):
                        db_refs.append(tenant_db.id.hex)
                        databases_manifest[tenant_db.id.hex] = _export_tenant_database(
                            writer, tenant_db
                        )

                    # Nested under the project, not a flat cross-org
                    # list — a bucket's name is only unique *within* its
                    # project, so a flat "bucket name -> files" mapping
                    # would be ambiguous the moment two projects had a
                    # same-named bucket.
                    bucket_payload = [
                        {
                            # Exported so a bound Environment can be
                            # re-linked to the *newly created* Bucket
                            # after restore (exports/restorer.py's
                            # bucket_by_old_id) -- the id itself is
                            # never reused as a real primary key on
                            # restore, only as a lookup key within this
                            # one package.
                            "id": bucket.id.hex,
                            "name": bucket.name,
                            "versioning_enabled": bucket.versioning_enabled,
                            "files": _export_bucket(writer, bucket, content_hash_to_arcname),
                        }
                        for bucket in project.buckets.order_by("name")
                    ]

                    projects_payload.append(
                        {"name": project.name, "tenant_databases": db_refs, "buckets": bucket_payload}
                    )
                workspaces_payload.append({"name": workspace.name, "projects": projects_payload})

            memberships_payload = []
            for membership in organization.memberships.select_related("user").filter(
                status=Membership.Status.ACTIVE
            ):
                role_slugs = list(
                    RoleAssignment.objects.filter(
                        user=membership.user, organization=organization, role__slug__in=SYSTEM_ROLES
                    ).values_list("role__slug", flat=True)
                )
                memberships_payload.append(
                    {
                        "email": membership.user.email,
                        "team": membership.team.name if membership.team else None,
                        "role_slugs": role_slugs,
                    }
                )

            teams_payload = list(organization.teams.order_by("name").values_list("name", flat=True))

            manifest["organization"] = {
                "name": organization.name,
                "slug": organization.slug,
                "workspaces": workspaces_payload,
                "teams": teams_payload,
                "memberships": memberships_payload,
            }
            manifest["databases"] = databases_manifest
            manifest["applications"] = _export_applications(organization)

            # manifest.json is written last, once everything else (and
            # therefore every other file's checksum) is known.
            zf.writestr("manifest.json", _json_dumps(manifest))

        tmp.seek(0)
        zip_bytes = tmp.read()

    container_bytes = container.write_container(zip_bytes, passphrase=passphrase)
    checksum = hashlib.sha256(container_bytes).hexdigest()
    return container_bytes, checksum


def _export_tenant_database(writer: _ArchiveWriter, tenant_db) -> dict:
    base = f"databases/{tenant_db.id.hex}"
    tables_payload = []

    for table in tenant_db.tables.order_by("created_at"):
        columns_payload = [
            _column_dict(c) for c in table.columns.order_by("created_at") if not c.is_primary_key
        ]
        fks_payload = [
            {
                "column": fk.column.name,
                "references_table": fk.references_table.name,
                "references_column": fk.references_column.name,
                "on_delete": fk.on_delete,
            }
            for fk in DBForeignKey.objects.filter(column__table=table).select_related(
                "column", "references_table", "references_column"
            )
        ]

        rows_arcname = f"{base}/rows/{table.id.hex}.csv"
        buf = io.StringIO()
        csv_writer = csv.writer(buf)
        for row in iter_export_rows(table):
            csv_writer.writerow(row)
        writer.write_bytes(rows_arcname, buf.getvalue().encode("utf-8"))

        tables_payload.append(
            {
                "id": table.id.hex,
                "name": table.name,
                "columns": columns_payload,
                "foreign_keys": fks_payload,
                "rows_path": rows_arcname,
            }
        )

    schema_arcname = f"{base}/schema.json"
    writer.write_bytes(schema_arcname, _json_dumps({"name": tenant_db.name, "tables": tables_payload}))

    return {"name": tenant_db.name, "schema_path": schema_arcname}


def _export_bucket(writer: _ArchiveWriter, bucket, content_hash_to_arcname: dict) -> list[dict]:
    client = get_client()
    files = FileObject.objects.filter(bucket=bucket, status=FileObject.Status.ACTIVE).select_related(
        "folder"
    )
    files_payload = []
    for file_obj in files:
        content_ref = content_hash_to_arcname.get(file_obj.checksum_sha256)
        if content_ref is None:
            content_ref = f"objects/{file_obj.checksum_sha256}"
            body = client.get_stream(file_obj.object_key)
            digest = writer.write_stream(content_ref, body.iter_chunks(1024 * 1024))
            # Trust the platform's own recorded checksum for
            # de-duplication lookups, but verify it against what was
            # actually read from storage right now — a mismatch means
            # the stored object and the catalog have drifted, which the
            # export must not paper over.
            if digest != file_obj.checksum_sha256:
                raise ValueError(
                    f"checksum mismatch reading {file_obj.object_key}: catalog says "
                    f"{file_obj.checksum_sha256}, storage has {digest}"
                )
            content_hash_to_arcname[file_obj.checksum_sha256] = content_ref

        files_payload.append(
            {
                "folder_path": _folder_path(file_obj.folder),
                "display_filename": file_obj.display_filename,
                "original_filename": file_obj.original_filename,
                "mime_type": file_obj.mime_type,
                "size": file_obj.size,
                "checksum_sha256": file_obj.checksum_sha256,
                "content_ref": content_ref,
            }
        )
    return files_payload


def _export_applications(organization) -> list[dict]:
    """Applications and their Environments -- metadata and non-secret
    configuration only. Deliberately excludes (see manifest.
    EXCLUDED_SCOPE): ApplicationCredential bearer tokens (no plaintext
    ever exists to export -- only a hash), EnvironmentSecret *values*
    (only key names travel, so a restore knows what to re-create), and
    EnvironmentWebhook signing secrets (regenerated fresh on restore).
    `tenant_database`/`bucket` bindings are recorded by the *same id*
    already used elsewhere in this manifest (databases_manifest's key,
    and the bucket payload's own new "id" field above) so restorer.py
    can re-link an Environment to the newly created database/bucket
    without a second export pass."""
    applications_payload = []
    for application in organization.applications.order_by("name"):
        environments_payload = []
        for environment in application.environments.order_by("name"):
            environments_payload.append(
                {
                    "name": environment.name,
                    "slug": environment.slug,
                    "environment_type": environment.environment_type,
                    "is_production_tier": environment.is_production_tier,
                    "status": environment.status,
                    "config": environment.config,
                    "tenant_database_ref": (
                        environment.tenant_database.id.hex
                        if hasattr(environment, "tenant_database")
                        else None
                    ),
                    "bucket_ref": environment.bucket.id.hex if hasattr(environment, "bucket") else None,
                    "variables": [
                        {"key": v.key, "value": v.value} for v in environment.variables.order_by("key")
                    ],
                    "webhooks": [
                        {"url": w.url, "event_types": w.event_types, "enabled": w.enabled}
                        for w in environment.webhooks.order_by("-created_at")
                    ],
                    # Names only -- see docstring above.
                    "secret_keys": list(environment.secrets.order_by("key").values_list("key", flat=True)),
                }
            )
        applications_payload.append(
            {
                "name": application.name,
                "description": application.description,
                "environments": environments_payload,
            }
        )
    return applications_payload


def _json_dumps(data: dict) -> bytes:
    import json

    return json.dumps(data, indent=2, sort_keys=True).encode("utf-8")
