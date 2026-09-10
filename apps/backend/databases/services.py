"""
The schema-change service layer. Every operation here follows the same
pipeline required by Section 9 of the master prompt: validate permission,
validate the requested schema, start a transaction, safely perform the
operation, save metadata, generate an audit event, gracefully roll back on
failure.

Two real connections are involved — `default` (control-plane catalog) and
`tenant` (the actual Postgres schema) — and there is no distributed
transaction spanning both (ADR-0001: they are deliberately separate
connections/databases). DDL is executed and committed on `tenant` first;
the catalog write on `default` happens second. If the catalog write fails
after the DDL already succeeded, a best-effort compensating DROP is
attempted so a schema/table doesn't silently exist without the catalog
knowing — this is a compensating action, not a guarantee (see
`_write_catalog`).
"""

import logging
import uuid

from django.db import IntegrityError as DjangoIntegrityError
from django.db import connections, transaction
from django.http import Http404
from psycopg import sql

from audit import services as audit
from audit.models import AuditEvent
from organizations.models import Membership
from permissions.services import has_permission

from .ddl import DDLValidationError, column_type_sql, default_clause_sql
from .identifiers import IdentifierError, validate_column_name, validate_identifier
from .models import DBColumn, DBForeignKey, DBIndex, DBTable, TenantDatabase

logger = logging.getLogger(__name__)


class SchemaPermissionDenied(Exception):
    pass


class SchemaValidationError(Exception):
    pass


def _require(actor, permission_code, organization_id, *, action, resource_type, resource_id, request_id):
    if not has_permission(actor, permission_code, organization_id=organization_id):
        audit.record(
            actor=actor,
            organization_id=organization_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request_id,
            result=AuditEvent.Result.DENIED,
        )
        raise SchemaPermissionDenied(f"{permission_code} required")


def _execute_tenant_ddl(ddl: sql.Composable) -> None:
    with transaction.atomic(using="tenant"), connections["tenant"].cursor() as cursor:
        cursor.execute(ddl)


def _require_unmanaged_schema(database, *, allow_managed_schema: bool = False):
    # App runtime provisioning uses these same services before publication.
    # After publication, ordinary structural changes require a coordinated
    # app migration -- `allow_managed_schema` is the one sanctioned
    # exception: app_platform.schema_evolution's own additive-only,
    # capability-checked path for extending an already-provisioned runtime
    # (Phase 3 step 3), passed explicitly by that module alone. No other
    # caller should ever pass it.
    if allow_managed_schema:
        return
    from app_platform.models import RuntimeProvision

    if RuntimeProvision.objects.filter(database_id=database.id).exists():
        raise SchemaValidationError("Managed application schema requires an application migration")


def _write_catalog(fn, *, compensating_ddl: sql.Composable | None = None):
    try:
        with transaction.atomic(using="default"):
            return fn()
    except Exception:
        if compensating_ddl is not None:
            try:
                _execute_tenant_ddl(compensating_ddl)
            except Exception:
                logger.exception(
                    "Compensating DDL also failed after a catalog write failure — "
                    "tenant schema and catalog have drifted; manual cleanup needed."
                )
        raise


def get_member_tenant_database(user, tenant_database_id) -> TenantDatabase:
    try:
        return TenantDatabase.objects.select_related("project__workspace__organization").get(
            id=tenant_database_id,
            project__workspace__organization__memberships__user=user,
            project__workspace__organization__memberships__status=Membership.Status.ACTIVE,
        )
    except TenantDatabase.DoesNotExist as exc:
        raise Http404 from exc


def get_member_table(user, table_id) -> DBTable:
    try:
        return DBTable.objects.select_related("tenant_database__project__workspace__organization").get(
            id=table_id,
            tenant_database__project__workspace__organization__memberships__user=user,
            tenant_database__project__workspace__organization__memberships__status=Membership.Status.ACTIVE,
        )
    except DBTable.DoesNotExist as exc:
        raise Http404 from exc


def get_member_column(user, column_id) -> DBColumn:
    try:
        return DBColumn.objects.select_related(
            "table__tenant_database__project__workspace__organization"
        ).get(
            id=column_id,
            table__tenant_database__project__workspace__organization__memberships__user=user,
            table__tenant_database__project__workspace__organization__memberships__status=Membership.Status.ACTIVE,
        )
    except DBColumn.DoesNotExist as exc:
        raise Http404 from exc


def create_tenant_database(
    *, actor, project, name: str, request_id: str = "", _database_id: uuid.UUID | None = None
) -> TenantDatabase:
    # Restore supplies a server-derived operation UUID, never an ID from
    # a request/archive. The public API does not expose this parameter.
    org_id = project.organization_id
    _require(
        actor,
        "database.create",
        org_id,
        action="database.create",
        resource_type="tenant_database",
        resource_id="",
        request_id=request_id,
    )

    if not name or len(name) > 200:
        raise SchemaValidationError("name must be between 1 and 200 characters")

    tenant_db = TenantDatabase(
        id=_database_id or uuid.uuid4(), project=project, name=name, created_by=actor
    )
    tenant_db.schema_name = f"db_{tenant_db.id.hex}"

    ddl = sql.SQL("CREATE SCHEMA {schema}").format(schema=sql.Identifier(tenant_db.schema_name))
    _execute_tenant_ddl(ddl)

    drop_ddl = sql.SQL("DROP SCHEMA {schema} CASCADE").format(schema=sql.Identifier(tenant_db.schema_name))
    _write_catalog(tenant_db.save, compensating_ddl=drop_ddl)

    audit.record(
        actor=actor,
        organization_id=org_id,
        action="database.create",
        resource_type="tenant_database",
        resource_id=tenant_db.id,
        request_id=request_id,
        context={"name": name},
    )
    return tenant_db


def create_table(
    *,
    actor,
    tenant_database: TenantDatabase,
    name: str,
    request_id: str = "",
    allow_managed_schema: bool = False,
) -> DBTable:
    org_id = tenant_database.organization_id
    _require(
        actor,
        "database.schema.manage",
        org_id,
        action="database.table.create",
        resource_type="tenant_database",
        resource_id=tenant_database.id,
        request_id=request_id,
    )
    _require_unmanaged_schema(tenant_database, allow_managed_schema=allow_managed_schema)

    try:
        validate_identifier(name, kind="table name")
    except IdentifierError as exc:
        raise SchemaValidationError(str(exc)) from exc

    table_id = uuid.uuid4()
    pk_column_id = uuid.uuid4()

    ddl = sql.SQL(
        "CREATE TABLE {schema}.{table} ({pk} UUID PRIMARY KEY DEFAULT gen_random_uuid())"
    ).format(
        schema=sql.Identifier(tenant_database.schema_name),
        table=sql.Identifier(name),
        pk=sql.Identifier("id"),
    )
    _execute_tenant_ddl(ddl)

    drop_ddl = sql.SQL("DROP TABLE {schema}.{table}").format(
        schema=sql.Identifier(tenant_database.schema_name), table=sql.Identifier(name)
    )

    def _write():
        table = DBTable.objects.create(
            id=table_id, tenant_database=tenant_database, name=name, created_by=actor
        )
        DBColumn.objects.create(
            id=pk_column_id,
            table=table,
            name="id",
            data_type=DBColumn.DataType.UUID,
            is_primary_key=True,
            is_nullable=False,
            is_unique=True,
        )
        return table

    table = _write_catalog(_write, compensating_ddl=drop_ddl)

    audit.record(
        actor=actor,
        organization_id=org_id,
        action="database.table.create",
        resource_type="db_table",
        resource_id=table.id,
        request_id=request_id,
        context={"name": name},
    )
    return table


def add_column(
    *,
    actor,
    table: DBTable,
    name: str,
    data_type: str,
    max_length: int | None = None,
    precision: int | None = None,
    scale: int | None = None,
    is_nullable: bool = True,
    is_unique: bool = False,
    is_indexed: bool = False,
    default_value=None,
    request_id: str = "",
    allow_managed_schema: bool = False,
) -> DBColumn:
    org_id = table.organization_id
    _require(
        actor,
        "database.schema.manage",
        org_id,
        action="database.column.create",
        resource_type="db_table",
        resource_id=table.id,
        request_id=request_id,
    )
    _require_unmanaged_schema(table.tenant_database, allow_managed_schema=allow_managed_schema)

    try:
        validate_column_name(name)
        type_sql = column_type_sql(data_type, max_length=max_length, precision=precision, scale=scale)
        default_sql = default_clause_sql(data_type, default_value)
    except (IdentifierError, DDLValidationError) as exc:
        raise SchemaValidationError(str(exc)) from exc

    null_sql = sql.SQL("") if is_nullable else sql.SQL(" NOT NULL")
    unique_sql = sql.SQL(" UNIQUE") if is_unique else sql.SQL("")

    # Pre-generated (matching create_table's table_id/pk_column_id
    # convention above) so a plain (non-unique) index's deterministic name
    # can be derived and issued in the same tenant-DDL pass as the column
    # itself, before the catalog row exists to read an id back from.
    column_id = uuid.uuid4()

    ddl = sql.SQL("ALTER TABLE {schema}.{table} ADD COLUMN {col} {type}{null}{unique}{default}").format(
        schema=sql.Identifier(table.tenant_database.schema_name),
        table=sql.Identifier(table.name),
        col=sql.Identifier(name),
        type=type_sql,
        null=null_sql,
        unique=unique_sql,
        default=default_sql,
    )
    drop_ddl = sql.SQL("ALTER TABLE {schema}.{table} DROP COLUMN {col}").format(
        schema=sql.Identifier(table.tenant_database.schema_name),
        table=sql.Identifier(table.name),
        col=sql.Identifier(name),
    )

    try:
        _execute_tenant_ddl(ddl)
    except DjangoIntegrityError as exc:
        # A brand-new UNIQUE column added to a table that already has 2+
        # rows: every existing row gets the same DEFAULT value (or NULL,
        # which never conflicts with anything else under Postgres UNIQUE
        # semantics -- only a non-NULL default can actually collide here).
        # The ALTER TABLE is one statement inside its own transaction, so
        # Postgres has already rolled it back in full -- no partial
        # column, no data loss; this is a clean, safe rejection to
        # surface, not a caught-and-hidden failure.
        raise SchemaValidationError(
            "Cannot add a unique column here: existing rows would violate the uniqueness "
            "constraint (they would all share the same default value)."
        ) from exc

    # A plain, non-unique index needs its own separate statement --
    # PostgreSQL has no inline "ADD COLUMN ... INDEX" syntax the way it
    # does for UNIQUE. Only reachable once the ADD COLUMN above has
    # already committed (each _execute_tenant_ddl call is its own
    # transaction), so a failure here needs its own compensating cleanup.
    index_name = f"idx_{column_id.hex}" if (is_indexed and not is_unique) else None
    if index_name:
        index_ddl = sql.SQL("CREATE INDEX {index} ON {schema}.{table} ({col})").format(
            index=sql.Identifier(index_name),
            schema=sql.Identifier(table.tenant_database.schema_name),
            table=sql.Identifier(table.name),
            col=sql.Identifier(name),
        )
        try:
            _execute_tenant_ddl(index_ddl)
        except Exception:
            try:
                _execute_tenant_ddl(drop_ddl)
            except Exception:
                logger.exception(
                    "Compensating column drop also failed after index creation failed -- "
                    "tenant schema and catalog have drifted; manual cleanup needed."
                )
            raise

    def _write():
        column = DBColumn.objects.create(
            id=column_id,
            table=table,
            name=name,
            data_type=data_type,
            max_length=max_length,
            precision=precision,
            scale=scale,
            is_nullable=is_nullable,
            is_unique=is_unique,
            default_value=default_value,
        )
        if is_unique:
            # "idx_" + a column UUID's hex (32 chars) = 36 chars — well
            # under the 63-byte Postgres identifier limit DBIndex.name is
            # meant to respect. The table+column combination used here
            # originally overflowed that limit (4 + 32 + 1 + 32 = 69
            # chars) — caught by actually creating a unique column, not by
            # inspection. Column IDs are already globally unique, so
            # there's no need for the table ID too.
            index = DBIndex.objects.create(table=table, name=f"idx_{column.id.hex}", is_unique=True)
            index.columns.add(column)
        elif index_name:
            index = DBIndex.objects.create(table=table, name=index_name, is_unique=False)
            index.columns.add(column)
        return column

    column = _write_catalog(_write, compensating_ddl=drop_ddl)

    audit.record(
        actor=actor,
        organization_id=org_id,
        action="database.column.create",
        resource_type="db_table",
        resource_id=table.id,
        request_id=request_id,
        context={"column": name, "data_type": data_type, "unique": is_unique, "indexed": bool(index_name)},
    )
    return column


def add_unique_constraint(
    *, actor, column: DBColumn, request_id: str = "", allow_managed_schema: bool = False
) -> DBIndex:
    """Retrofits a UNIQUE constraint onto an EXISTING, already-materialized
    column -- add_column's own `is_unique=True` only ever applies at
    column-creation time. Idempotent: if this column is already unique,
    returns its existing DBIndex rather than re-issuing DDL or raising, so
    re-running the same schema-evolution step twice is always safe. A
    genuine duplicate-value conflict is surfaced as a clean
    SchemaValidationError, never a bare 500 -- ADD CONSTRAINT is one
    statement inside one transaction, so Postgres has already rolled the
    whole thing back before this function's caller ever sees the error:
    no partial constraint, no data loss, no rewritten or deleted rows."""
    table = column.table
    org_id = table.organization_id
    _require(
        actor,
        "database.schema.manage",
        org_id,
        action="database.column.unique.add",
        resource_type="db_table",
        resource_id=table.id,
        request_id=request_id,
    )
    _require_unmanaged_schema(table.tenant_database, allow_managed_schema=allow_managed_schema)

    if column.is_unique:
        existing = DBIndex.objects.filter(table=table, columns=column, is_unique=True).first()
        if existing is not None:
            return existing
        raise SchemaValidationError("Column is marked unique but has no matching index record.")

    index_name = f"idx_{column.id.hex}"
    ddl = sql.SQL("ALTER TABLE {schema}.{table} ADD CONSTRAINT {name} UNIQUE ({col})").format(
        schema=sql.Identifier(table.tenant_database.schema_name),
        table=sql.Identifier(table.name),
        name=sql.Identifier(index_name),
        col=sql.Identifier(column.name),
    )
    drop_ddl = sql.SQL("ALTER TABLE {schema}.{table} DROP CONSTRAINT {name}").format(
        schema=sql.Identifier(table.tenant_database.schema_name),
        table=sql.Identifier(table.name),
        name=sql.Identifier(index_name),
    )
    try:
        _execute_tenant_ddl(ddl)
    except DjangoIntegrityError as exc:
        raise SchemaValidationError(
            "Cannot add a unique constraint: existing values in this column are not unique."
        ) from exc

    def _write():
        column.is_unique = True
        column.save(update_fields=["is_unique"])
        index = DBIndex.objects.create(table=table, name=index_name, is_unique=True)
        index.columns.add(column)
        return index

    index = _write_catalog(_write, compensating_ddl=drop_ddl)

    audit.record(
        actor=actor,
        organization_id=org_id,
        action="database.column.unique.add",
        resource_type="db_table",
        resource_id=table.id,
        request_id=request_id,
        context={"column": column.name},
    )
    return index


def add_index(
    *, actor, column: DBColumn, request_id: str = "", allow_managed_schema: bool = False
) -> DBIndex:
    """Retrofits a plain (non-unique) B-tree index onto an EXISTING
    column. Idempotent for the same reason as add_unique_constraint above
    -- a column that's already unique (which already carries a real
    index) or already separately indexed returns its existing DBIndex
    rather than issuing a duplicate CREATE INDEX."""
    table = column.table
    org_id = table.organization_id
    _require(
        actor,
        "database.schema.manage",
        org_id,
        action="database.column.index.add",
        resource_type="db_table",
        resource_id=table.id,
        request_id=request_id,
    )
    _require_unmanaged_schema(table.tenant_database, allow_managed_schema=allow_managed_schema)

    existing = DBIndex.objects.filter(table=table, columns=column).first()
    if existing is not None:
        return existing

    index_name = f"idx_{column.id.hex}"
    ddl = sql.SQL("CREATE INDEX {index} ON {schema}.{table} ({col})").format(
        index=sql.Identifier(index_name),
        schema=sql.Identifier(table.tenant_database.schema_name),
        table=sql.Identifier(table.name),
        col=sql.Identifier(column.name),
    )
    drop_ddl = sql.SQL("DROP INDEX {schema}.{index}").format(
        schema=sql.Identifier(table.tenant_database.schema_name), index=sql.Identifier(index_name)
    )
    _execute_tenant_ddl(ddl)

    def _write():
        index = DBIndex.objects.create(table=table, name=index_name, is_unique=False)
        index.columns.add(column)
        return index

    index = _write_catalog(_write, compensating_ddl=drop_ddl)

    audit.record(
        actor=actor,
        organization_id=org_id,
        action="database.column.index.add",
        resource_type="db_table",
        resource_id=table.id,
        request_id=request_id,
        context={"column": column.name},
    )
    return index


_ON_DELETE_SQL: dict[str, sql.SQL] = {
    DBForeignKey.OnDelete.CASCADE.value: sql.SQL("CASCADE"),
    DBForeignKey.OnDelete.RESTRICT.value: sql.SQL("RESTRICT"),
    DBForeignKey.OnDelete.SET_NULL.value: sql.SQL("SET NULL"),
}


def add_foreign_key(
    *,
    actor,
    column: DBColumn,
    references_table: DBTable,
    references_column: DBColumn,
    on_delete: str = DBForeignKey.OnDelete.RESTRICT,
    request_id: str = "",
    allow_managed_schema: bool = False,
) -> DBForeignKey:
    org_id = column.organization_id
    _require(
        actor,
        "database.schema.manage",
        org_id,
        action="database.foreign_key.create",
        resource_type="db_column",
        resource_id=column.id,
        request_id=request_id,
    )
    _require_unmanaged_schema(column.table.tenant_database, allow_managed_schema=allow_managed_schema)

    if references_table.tenant_database_id != column.table.tenant_database_id:
        raise SchemaValidationError("Foreign keys must reference a table in the same database")
    if not (references_column.is_unique or references_column.is_primary_key):
        raise SchemaValidationError("Foreign keys must reference a primary key or unique column")
    if column.data_type != references_column.data_type:
        raise SchemaValidationError("Foreign key column type must match the referenced column type")
    if hasattr(column, "foreign_key"):
        raise SchemaValidationError("Column already has a foreign key")
    if on_delete == DBForeignKey.OnDelete.SET_NULL and not column.is_nullable:
        raise SchemaValidationError("ON DELETE SET NULL requires a nullable column")
    if on_delete not in _ON_DELETE_SQL:
        raise SchemaValidationError(f"Unsupported on_delete: {on_delete!r}")

    constraint_name = f"fk_{column.id.hex}"
    ddl = sql.SQL(
        "ALTER TABLE {schema}.{table} ADD CONSTRAINT {constraint} "
        "FOREIGN KEY ({col}) REFERENCES {schema}.{ref_table} ({ref_col}) ON DELETE {on_delete}"
    ).format(
        schema=sql.Identifier(column.table.tenant_database.schema_name),
        table=sql.Identifier(column.table.name),
        constraint=sql.Identifier(constraint_name),
        col=sql.Identifier(column.name),
        ref_table=sql.Identifier(references_table.name),
        ref_col=sql.Identifier(references_column.name),
        on_delete=_ON_DELETE_SQL[on_delete],
    )
    _execute_tenant_ddl(ddl)

    drop_ddl = sql.SQL("ALTER TABLE {schema}.{table} DROP CONSTRAINT {constraint}").format(
        schema=sql.Identifier(column.table.tenant_database.schema_name),
        table=sql.Identifier(column.table.name),
        constraint=sql.Identifier(constraint_name),
    )

    def _write():
        return DBForeignKey.objects.create(
            column=column,
            references_table=references_table,
            references_column=references_column,
            on_delete=on_delete,
        )

    fk = _write_catalog(_write, compensating_ddl=drop_ddl)

    audit.record(
        actor=actor,
        organization_id=org_id,
        action="database.foreign_key.create",
        resource_type="db_column",
        resource_id=column.id,
        request_id=request_id,
        context={"references_table": references_table.name, "references_column": references_column.name},
    )
    return fk


def delete_table(*, actor, table: DBTable, request_id: str = "") -> None:
    org_id = table.organization_id
    _require(
        actor,
        "database.delete",
        org_id,
        action="database.table.delete",
        resource_type="db_table",
        resource_id=table.id,
        request_id=request_id,
    )
    _require_unmanaged_schema(table.tenant_database)

    ddl = sql.SQL("DROP TABLE {schema}.{table}").format(
        schema=sql.Identifier(table.tenant_database.schema_name), table=sql.Identifier(table.name)
    )
    _execute_tenant_ddl(ddl)

    table_id = table.id
    with transaction.atomic(using="default"):
        table.delete()

    audit.record(
        actor=actor,
        organization_id=org_id,
        action="database.table.delete",
        resource_type="db_table",
        resource_id=table_id,
        request_id=request_id,
    )


def delete_tenant_database(*, actor, tenant_database: TenantDatabase, request_id: str = "") -> None:
    """Drops the entire physical schema — CASCADE, so every table in it
    goes too. This is a "Drop Database" operation, distinct from any
    lighter-weight delete/archive/disconnect (Section 21 of the master
    prompt); the client is responsible for an explicit, unambiguous
    confirmation before calling this."""
    org_id = tenant_database.organization_id
    _require(
        actor,
        "database.delete",
        org_id,
        action="database.drop",
        resource_type="tenant_database",
        resource_id=tenant_database.id,
        request_id=request_id,
    )
    _require_unmanaged_schema(tenant_database)

    ddl = sql.SQL("DROP SCHEMA {schema} CASCADE").format(schema=sql.Identifier(tenant_database.schema_name))
    _execute_tenant_ddl(ddl)

    db_id = tenant_database.id
    with transaction.atomic(using="default"):
        tenant_database.delete()

    audit.record(
        actor=actor,
        organization_id=org_id,
        action="database.drop",
        resource_type="tenant_database",
        resource_id=db_id,
        request_id=request_id,
    )
