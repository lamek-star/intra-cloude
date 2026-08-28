"""
Restores a .icp package into a brand-new Organization (the only target
this first implementation supports — restoring *into* an existing
organization needs a conflict-resolution policy this doesn't have yet,
tracked as an open item). Schema and rows are rebuilt exclusively
through the same validated service functions the live database builder
and file-upload pipeline already use
(`databases.services.create_tenant_database/create_table/add_column/
add_foreign_key`, `storage.services.upload_file`) — restore never
executes raw DDL or SQL text from the package (Section 17 of the master
prompt: "restore never executes raw SQL from the package").

Because the target organization doesn't exist until this function
returns, "staged" restore here means exactly that: nothing is visible
or reachable until the whole thing succeeds. Unlike the live schema
builder's one-edit-at-a-time "compensating DROP, not a guarantee"
(`databases/services.py::_write_catalog` — necessary there because
each edit commits independently as a user makes it), a restore is one
bulk operation: PostgreSQL supports transactional DDL, so wrapping the
whole thing in a single `transaction.atomic(using="tenant")` alongside
`transaction.atomic(using="default")` for the catalog gives a real
all-or-nothing guarantee on both connections, not a best-effort one.
The one exception is object storage (uploaded file bytes): it isn't
transactional at all, so a rolled-back restore can leave orphaned
objects behind — wasted storage, not a correctness problem, since no
catalog row ever references them. A cleanup sweep for that is a known
gap, not implemented here.
"""

import csv
import hashlib
import io
import json
import uuid
import zipfile
import zlib
from dataclasses import dataclass, field

from django.core.files.base import ContentFile
from django.db import connections, transaction
from django.utils.text import slugify
from psycopg import sql

from databases import services as db_services
from databases.models import DBColumn
from imports.services import _convert_value
from organizations.models import Membership, Organization, Team
from organizations.services import create_organization
from permissions.services import assign_role
from storage.models import Bucket, Folder
from storage.services import UploadTooLarge, upload_file
from workspaces.models import Project, Workspace

from . import container
from .manifest import validate_manifest_shape


class RestoreError(Exception):
    pass


class PackageValidationError(RestoreError):
    pass


# A corrupted archive member can surface as any of three different
# exception types depending on exactly where the corruption lands:
# zipfile.BadZipFile at ZipFile() construction (malformed central
# directory), zlib.error while decompressing a member's data (a broken
# compressed stream), or zipfile.BadZipFile "Bad CRC-32" *after*
# successful decompression, checked lazily on read() rather than at
# open time. All three mean the same thing to a caller — reject the
# package — so every place that reads a member's bytes needs to catch
# all three, not just the first one encountered while writing this.
_CORRUPT_ARCHIVE_ERRORS = (zipfile.BadZipFile, zlib.error)


@dataclass
class RestoreReport:
    organization_id: str | None = None
    organization_name: str | None = None
    workspaces: int = 0
    projects: int = 0
    tenant_databases: int = 0
    tables: int = 0
    rows_imported: int = 0
    buckets: int = 0
    files_restored: int = 0
    files_quarantined: int = 0
    teams: int = 0
    memberships_restored: int = 0
    memberships_skipped: list[str] = field(default_factory=list)
    applications: int = 0
    environments: int = 0
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "organization_id": self.organization_id,
            "organization_name": self.organization_name,
            "workspaces": self.workspaces,
            "projects": self.projects,
            "tenant_databases": self.tenant_databases,
            "tables": self.tables,
            "rows_imported": self.rows_imported,
            "buckets": self.buckets,
            "files_restored": self.files_restored,
            "files_quarantined": self.files_quarantined,
            "teams": self.teams,
            "memberships_restored": self.memberships_restored,
            "memberships_skipped": self.memberships_skipped,
            "applications": self.applications,
            "environments": self.environments,
            "warnings": self.warnings,
        }


def open_package(container_bytes: bytes, *, passphrase: str | None = None) -> tuple[zipfile.ZipFile, dict]:
    """Step 1-3 of Section 17's restore state machine: decrypt if
    needed, open the archive, parse and structurally validate the
    manifest. Does NOT yet verify per-file checksums — that needs the
    zip's member list, done by the caller via `verify_checksums` so a
    caller can report progress/size before committing to reading every
    byte."""
    zip_bytes = container.read_container_payload(container_bytes, passphrase=passphrase)
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as exc:
        raise PackageValidationError("not a valid package: corrupt archive") from exc

    try:
        manifest = json.loads(zf.read("manifest.json"))
    except KeyError as exc:
        raise PackageValidationError("not a valid package: missing manifest.json") from exc
    except json.JSONDecodeError as exc:
        raise PackageValidationError("not a valid package: corrupt manifest.json") from exc
    except _CORRUPT_ARCHIVE_ERRORS as exc:
        # zipfile validates each member's data lazily, on read — not at
        # ZipFile() construction time — so a corrupted manifest.json
        # surfaces here, not in the `except zipfile.BadZipFile` above.
        raise PackageValidationError("not a valid package: corrupt manifest.json") from exc

    validate_manifest_shape(manifest)
    return zf, manifest


def verify_checksums(zf: zipfile.ZipFile, manifest: dict) -> None:
    """Step 2 of Section 17: every file the manifest claims to describe
    must actually match its recorded sha256 — corruption or tampering
    is caught here, before a single database row is touched."""
    for arcname, expected in manifest.get("checksums", {}).items():
        try:
            data = zf.read(arcname)
        except KeyError as exc:
            raise PackageValidationError(
                f"package is missing a file its manifest describes: {arcname}"
            ) from exc
        except _CORRUPT_ARCHIVE_ERRORS as exc:
            # Same lazy-validation-on-read behavior as open_package — a
            # tampered/corrupted data file (not just manifest.json)
            # surfaces here, on this file's own read().
            raise PackageValidationError(f"corrupt data for {arcname}") from exc
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected:
            raise PackageValidationError(
                f"checksum mismatch for {arcname} — package is corrupted or tampered with"
            )


def restore_package(zf: zipfile.ZipFile, manifest: dict, *, actor) -> RestoreReport:
    """The actual restore, wrapped in one real transaction on *each* of
    the two physical connections involved (`default` for the catalog,
    `tenant` for schema DDL + row data — ADR-0001's control-plane/data-
    plane separation means these are genuinely separate databases, so
    one transaction can't span both). Unlike the live, one-operation-
    at-a-time schema builder (databases/services.py's "compensating
    DROP, not a guarantee" — necessary there because each edit commits
    independently as a user makes it), a restore is one bulk operation
    end to end: PostgreSQL supports transactional DDL, so wrapping all
    of it in a single `transaction.atomic(using="tenant")` gives a real
    all-or-nothing guarantee here, not a best-effort one. Every call
    into `databases.services`/`storage.services` below opens its own
    nested `atomic()` block on one of these same connections, which
    Django correctly turns into a savepoint rather than a competing
    transaction."""
    report = RestoreReport()
    org_data = manifest["organization"]

    with transaction.atomic(using="default"), transaction.atomic(using="tenant"):
        # A restore's whole point is to reproduce the source
        # organization, name included — but `Organization.slug` is
        # globally unique, and the source organization (this is a
        # brand-new one, not a replacement) very plausibly still exists
        # with that exact slug, whether on this installation or because
        # the same package is imported twice. create_organization's own
        # slugify(name) default would collide; generate one that can't.
        slug = f"{slugify(org_data['name'])}-{uuid.uuid4().hex[:8]}"
        while Organization.objects.filter(slug=slug).exists():
            slug = f"{slugify(org_data['name'])}-{uuid.uuid4().hex[:8]}"
        organization = create_organization(name=org_data["name"], created_by=actor, slug=slug)
        report.organization_id = str(organization.id)
        report.organization_name = organization.name

        team_by_name = {}
        for team_name in org_data.get("teams", []):
            team_by_name[team_name] = Team.objects.create(organization=organization, name=team_name)
            report.teams += 1

        # Keyed by the *old* manifest id (databases_manifest's key /
        # the bucket payload's own "id" field) so an Application's
        # Environment binding, restored afterward, can re-link to the
        # newly created row without a second export pass.
        tenant_database_by_old_id: dict[str, object] = {}
        bucket_by_old_id: dict[str, object] = {}

        for ws_data in org_data.get("workspaces", []):
            workspace = Workspace.objects.create(
                organization=organization, name=ws_data["name"], created_by=actor
            )
            report.workspaces += 1

            for proj_data in ws_data.get("projects", []):
                project = Project.objects.create(
                    workspace=workspace, name=proj_data["name"], created_by=actor
                )
                report.projects += 1

                for db_id in proj_data.get("tenant_databases", []):
                    db_manifest_entry = manifest["databases"][db_id]
                    tenant_database_by_old_id[db_id] = _restore_tenant_database(
                        zf, db_manifest_entry, project=project, actor=actor, report=report
                    )

                for bucket_data in proj_data.get("buckets", []):
                    bucket = _restore_bucket(zf, bucket_data, project=project, actor=actor, report=report)
                    if bucket_data.get("id"):
                        bucket_by_old_id[bucket_data["id"]] = bucket

        _restore_applications(
            manifest.get("applications", []),
            organization=organization,
            actor=actor,
            tenant_database_by_old_id=tenant_database_by_old_id,
            bucket_by_old_id=bucket_by_old_id,
            report=report,
        )

        _restore_memberships(
            org_data.get("memberships", []),
            organization=organization,
            team_by_name=team_by_name,
            report=report,
        )

    return report


def _restore_tenant_database(zf: zipfile.ZipFile, db_entry: dict, *, project, actor, report: RestoreReport):
    schema = json.loads(zf.read(db_entry["schema_path"]))
    tenant_db = db_services.create_tenant_database(actor=actor, project=project, name=schema["name"])
    report.tenant_databases += 1

    tables_by_name = {}
    columns_by_ref: dict[tuple[str, str], DBColumn] = {}

    for table_data in schema["tables"]:
        table = db_services.create_table(actor=actor, tenant_database=tenant_db, name=table_data["name"])
        tables_by_name[table_data["name"]] = table
        report.tables += 1
        # create_table auto-creates the "id" primary key column, which
        # builder.py deliberately excludes from schema.json's columns
        # list (add_column can't be used to (re)create it) — but a
        # foreign key can reference it, so it still needs an entry here.
        columns_by_ref[(table_data["name"], "id")] = table.columns.get(is_primary_key=True)
        for col_data in table_data["columns"]:
            column = db_services.add_column(
                actor=actor,
                table=table,
                name=col_data["name"],
                data_type=col_data["data_type"],
                max_length=col_data["max_length"],
                precision=col_data["precision"],
                scale=col_data["scale"],
                is_nullable=col_data["is_nullable"],
                is_unique=col_data["is_unique"],
                default_value=col_data["default_value"],
            )
            columns_by_ref[(table_data["name"], col_data["name"])] = column

    for table_data in schema["tables"]:
        table = tables_by_name[table_data["name"]]
        for fk_data in table_data["foreign_keys"]:
            db_services.add_foreign_key(
                actor=actor,
                column=columns_by_ref[(table_data["name"], fk_data["column"])],
                references_table=tables_by_name[fk_data["references_table"]],
                references_column=columns_by_ref[(fk_data["references_table"], fk_data["references_column"])],
                on_delete=fk_data["on_delete"],
            )

    # Insert rows in FK-dependency order (a referenced row must exist
    # before the row that references it) — a plain per-table loop in
    # manifest order would fail the moment any table has a foreign key.
    for table_data in _topological_order(schema["tables"]):
        table = tables_by_name[table_data["name"]]
        report.rows_imported += _restore_rows(zf, table_data, table=table)

    return tenant_db


def _topological_order(tables_data: list[dict]) -> list[dict]:
    by_name = {t["name"]: t for t in tables_data}
    resolved: list[dict] = []
    resolved_names: set[str] = set()
    remaining = list(tables_data)

    while remaining:
        progressed = False
        still_remaining = []
        for table_data in remaining:
            deps = {
                fk["references_table"]
                for fk in table_data["foreign_keys"]
                if fk["references_table"] != table_data["name"]
            }
            if deps <= resolved_names:
                resolved.append(table_data)
                resolved_names.add(table_data["name"])
                progressed = True
            else:
                still_remaining.append(table_data)
        remaining = still_remaining
        if not progressed and remaining:
            # A genuine FK cycle — the source system couldn't have
            # inserted this data either (constraints aren't deferrable
            # here), so this can only mean the package is corrupt.
            raise RestoreError(
                f"cannot resolve foreign-key insertion order for tables: {[t['name'] for t in remaining]}"
            )
    return [by_name[t["name"]] for t in resolved]


def _restore_rows(zf: zipfile.ZipFile, table_data: dict, *, table) -> int:
    raw = zf.read(table_data["rows_path"]).decode("utf-8")
    reader = csv.reader(io.StringIO(raw))
    header = next(reader, None)
    if header is None:
        return 0

    columns_by_name = {c.name: c for c in table.columns.all()}
    target_types = [columns_by_name[name].data_type for name in header]

    insert_sql = sql.SQL("INSERT INTO {schema}.{table} ({cols}) VALUES ({placeholders})").format(
        schema=sql.Identifier(table.tenant_database.schema_name),
        table=sql.Identifier(table.name),
        cols=sql.SQL(", ").join(sql.Identifier(c) for c in header),
        placeholders=sql.SQL(", ").join(sql.Placeholder() for _ in header),
    )

    count = 0
    with connections["tenant"].cursor() as cursor:
        for row in reader:
            values = [
                _convert_value(raw_value, data_type)
                for raw_value, data_type in zip(row, target_types, strict=True)
            ]
            cursor.execute(insert_sql, values)
            count += 1
    return count


def _restore_bucket(
    zf: zipfile.ZipFile, bucket_data: dict, *, project, actor, report: RestoreReport
) -> Bucket:
    bucket = Bucket.objects.create(
        project=project,
        name=bucket_data["name"],
        versioning_enabled=bucket_data["versioning_enabled"],
        created_by=actor,
    )
    report.buckets += 1

    folder_cache: dict[tuple[str, ...], Folder | None] = {(): None}

    def _get_or_create_folder(path: tuple[str, ...]) -> Folder | None:
        if path in folder_cache:
            return folder_cache[path]
        parent = _get_or_create_folder(path[:-1])
        folder = Folder.objects.create(bucket=bucket, parent=parent, name=path[-1], created_by=actor)
        folder_cache[path] = folder
        return folder

    for file_data in bucket_data["files"]:
        folder = _get_or_create_folder(tuple(file_data["folder_path"]))
        content = zf.read(file_data["content_ref"])
        try:
            file_obj = upload_file(
                bucket=bucket,
                folder=folder,
                uploaded_file=ContentFile(content, name=file_data["original_filename"]),
                display_filename=file_data["display_filename"],
                creator=actor,
            )
        except UploadTooLarge:
            report.warnings.append(
                f"skipped {file_data['display_filename']!r}: exceeds this installation's upload size limit"
            )
            continue

        if file_obj.status == "quarantined":
            report.files_quarantined += 1
        report.files_restored += 1

        if file_obj.checksum_sha256 != file_data["checksum_sha256"]:
            report.warnings.append(
                f"{file_data['display_filename']!r} restored but checksum differs from the export "
                "(byte-for-byte mismatch) — investigate before trusting this file"
            )

    return bucket


def _restore_applications(
    applications_data: list[dict],
    *,
    organization,
    actor,
    tenant_database_by_old_id: dict,
    bucket_by_old_id: dict,
    report: RestoreReport,
) -> None:
    """Recreates each Application through applications.services.
    register_application (the exact same path a real "create application"
    API call uses -- never a raw model .create() bypassing its
    ServiceAccount/Membership bootstrap), then each Environment through
    environments.services.create_environment, re-linking database/
    storage bindings by the old-id lookups built while restoring
    workspaces/projects above. Secret keys are recreated as a warning
    listing what must be re-entered, never as an EnvironmentSecret with
    an empty or placeholder value -- an EnvironmentSecret row existing
    at all is meant to mean "a real secret is stored here"."""
    from applications import services as application_services
    from environments import services as environment_services

    for app_data in applications_data:
        application = application_services.register_application(
            organization=organization,
            name=app_data["name"],
            description=app_data.get("description", ""),
            owner=actor,
        )
        report.applications += 1

        for env_data in app_data.get("environments", []):
            environment = environment_services.create_environment(
                application=application,
                name=env_data["name"],
                environment_type=env_data["environment_type"],
                is_production_tier=env_data["is_production_tier"],
                config=env_data.get("config") or {},
                actor=actor,
                slug=env_data.get("slug"),
            )
            report.environments += 1

            # Set from the *forward* side (TenantDatabase.environment /
            # Bucket.environment own the actual FK column) and saved
            # explicitly -- assigning through Environment's reverse
            # one-to-one accessor only updates in-memory descriptor
            # caches, it does not persist anything on its own.
            tenant_database_ref = env_data.get("tenant_database_ref")
            if tenant_database_ref and tenant_database_ref in tenant_database_by_old_id:
                bound_database = tenant_database_by_old_id[tenant_database_ref]
                bound_database.environment = environment
                bound_database.save(update_fields=["environment"])
            bucket_ref = env_data.get("bucket_ref")
            if bucket_ref and bucket_ref in bucket_by_old_id:
                bound_bucket = bucket_by_old_id[bucket_ref]
                bound_bucket.environment = environment
                bound_bucket.save(update_fields=["environment"])

            for var_data in env_data.get("variables", []):
                environment_services.set_variable(
                    environment=environment, key=var_data["key"], value=var_data["value"], actor=actor
                )
            for webhook_data in env_data.get("webhooks", []):
                environment_services.create_webhook(
                    environment=environment,
                    url=webhook_data["url"],
                    event_types=webhook_data.get("event_types", []),
                    enabled=webhook_data.get("enabled", True),
                    actor=actor,
                )
            secret_keys = env_data.get("secret_keys", [])
            if secret_keys:
                report.warnings.append(
                    f"environment {app_data['name']!r}/{env_data['name']!r}: "
                    f"{len(secret_keys)} secret(s) were not restored (values are never exported) "
                    f"and must be re-created: {', '.join(secret_keys)}"
                )


def _restore_memberships(
    memberships: list[dict], *, organization, team_by_name: dict, report: RestoreReport
) -> None:
    from accounts.models import User

    for entry in memberships:
        try:
            user = User.objects.get(email__iexact=entry["email"])
        except User.DoesNotExist:
            report.memberships_skipped.append(entry["email"])
            continue

        membership, _created = Membership.objects.get_or_create(
            user=user,
            organization=organization,
            defaults={
                "status": Membership.Status.ACTIVE,
                "team": team_by_name.get(entry.get("team")) if entry.get("team") else None,
            },
        )
        for role_slug in entry.get("role_slugs", []):
            if role_slug == "organization-administrator":
                continue  # the restoring actor already holds this from create_organization
            try:
                assign_role(user=user, role_slug=role_slug, organization=organization, granted_by=None)
            except Exception as exc:  # noqa: BLE001 - a bad/legacy role slug shouldn't abort the whole restore
                report.warnings.append(f"could not restore role {role_slug!r} for {entry['email']}: {exc}")
        report.memberships_restored += 1
