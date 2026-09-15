"""Typed record CRUD over a provisioned app runtime.

Field/relationship values in the API are keyed by their definition UUID
(the same id the model/field/relationship endpoints already use), never by
physical column name -- callers should never need to know a runtime's
generated schema. Actual storage and type/required validation is delegated
to `databases.rows`/`databases.values` against the real table the runtime
provisioning step built; this module only translates definition ids to/from
the physical column names `runtime_plan.physical_name` deterministically
assigns, and layers the same `database.read`/`database.write` authorization
the generic data explorer already enforces (see PERMISSIONS.md's "Generated
records remain under the existing database permissions" decision -- this is
not a second, parallel enforcement path).
"""

from dataclasses import dataclass

from django.db import Error as DjangoDatabaseError
from django.db import IntegrityError as DjangoIntegrityError
from django.db import connections, transaction
from django.http import Http404
from psycopg import errors as psycopg_errors
from psycopg import sql

from audit import services as audit
from audit.models import AuditEvent
from databases import rows as row_ops
from databases.models import DBTable
from databases.values import RowValueError
from permissions.services import has_permission

from .models import ModelDefinition, RecordAttachment, RuntimeProvision
from .runtime_plan import physical_name

RESOURCE_TYPE_TENANT_DATABASE = "databases.tenant_database"


class RecordAccessDenied(Exception):
    pass


class RecordValueError(Exception):
    pass


def _resource(tenant_database_id):
    return (RESOURCE_TYPE_TENANT_DATABASE, tenant_database_id)


def _receipt(model: ModelDefinition) -> RuntimeProvision:
    try:
        receipt = RuntimeProvision.objects.select_related("database").get(instance=model.instance)
    except RuntimeProvision.DoesNotExist as exc:
        raise Http404("This app has no provisioned runtime yet.") from exc
    if not receipt.completed_at or receipt.database_id is None:
        raise Http404("Runtime provisioning has not completed yet.")
    return receipt


def _require(actor, model: ModelDefinition, capability: str, *, action: str) -> RuntimeProvision:
    instance = model.instance
    receipt = _receipt(model)
    allowed = has_permission(
        actor, capability, organization_id=instance.organization_id, resource=_resource(receipt.database_id)
    )
    if not allowed:
        audit.record(
            actor=actor,
            organization_id=instance.organization_id,
            action=action,
            resource_type="app_model",
            resource_id=model.id,
            result=AuditEvent.Result.DENIED,
        )
        raise RecordAccessDenied(f"{capability} required")
    return receipt


def _table(receipt: RuntimeProvision, model: ModelDefinition) -> DBTable:
    table_id = receipt.bindings.get("models", {}).get(str(model.id))
    if table_id is None:
        raise Http404("Model has no runtime table.")
    return DBTable.objects.select_related("tenant_database").get(pk=table_id)


def resolve(
    actor, model: ModelDefinition, capability: str, *, action: str
) -> tuple[RuntimeProvision, DBTable]:
    """Authorization + runtime-table resolution shared with attachments.py,
    which needs the exact same "is this actor allowed at this record" check
    without duplicating it."""
    receipt = _require(actor, model, capability, action=action)
    return receipt, _table(receipt, model)


def record_exists(table: DBTable, record_id) -> bool:
    try:
        row_ops.get_row(table, record_id)
    except row_ops.RowNotFound:
        return False
    return True


@dataclass(frozen=True)
class _ScalarField:
    column: str


@dataclass(frozen=True)
class _ManyToManyField:
    # A join table's two FK columns are always the fixed literal names
    # "source_id"/"target_id" (runtime_build._build_join_table,
    # schema_evolution._add_join_table_to_runtime) -- never a per-identity
    # UUID-hex name -- so no DBColumn lookup is needed to know them, only
    # which one is "this model's own side" for a given relationship.
    join_table_id: str
    own_column: str
    other_column: str
    writable: bool


_Mapping = _ScalarField | _ManyToManyField


def _field_map(receipt: RuntimeProvision, model: ModelDefinition) -> dict[str, _Mapping]:
    """definition id (str) -> field/relationship mapping, covering this
    model's own fields, its outgoing relationships (many_to_one is a real
    column on its own table; many_to_many is a join table, writable from
    this, the source, side), and its INCOMING many_to_many relationships
    (read-only from this, the target, side -- incoming many_to_one stays
    entirely absent/out of scope, unchanged from before this)."""
    mapping: dict[str, _Mapping] = {
        str(field.id): _ScalarField(physical_name("f", str(field.id))) for field in model.fields.all()
    }
    for rel in model.outgoing.all():
        if rel.kind == "many_to_many":
            binding = receipt.bindings["relationships"][str(rel.id)]
            mapping[str(rel.id)] = _ManyToManyField(
                join_table_id=binding["join_table"],
                own_column="source_id",
                other_column="target_id",
                writable=True,
            )
        else:
            mapping[str(rel.id)] = _ScalarField(physical_name("r", str(rel.id)))
    for rel in model.incoming.all():
        if rel.kind != "many_to_many":
            continue
        binding = receipt.bindings["relationships"][str(rel.id)]
        mapping[str(rel.id)] = _ManyToManyField(
            join_table_id=binding["join_table"],
            own_column="target_id",
            other_column="source_id",
            writable=False,
        )
    return mapping


def _m2m_mappings(field_map: dict[str, _Mapping]) -> dict[str, _ManyToManyField]:
    return {
        definition_id: mapping
        for definition_id, mapping in field_map.items()
        if isinstance(mapping, _ManyToManyField)
    }


def _resolve_join_tables(mappings: dict[str, _ManyToManyField]) -> dict[str, DBTable]:
    ids = {mapping.join_table_id for mapping in mappings.values()}
    if not ids:
        return {}
    tables = DBTable.objects.select_related("tenant_database").filter(pk__in=ids)
    return {str(table.id): table for table in tables}


def _translate_in(field_map: dict[str, _Mapping], data: dict) -> tuple[dict, dict[str, list]]:
    if not isinstance(data, dict):
        raise RecordValueError("expected an object")
    row_data: dict = {}
    m2m_data: dict[str, list] = {}
    for definition_id, value in data.items():
        mapping = field_map.get(definition_id)
        if mapping is None:
            raise RecordValueError(f"unknown field or relationship: {definition_id}")
        if isinstance(mapping, _ManyToManyField):
            if not mapping.writable:
                raise RecordValueError(f"{definition_id} can only be written from its source side")
            if value is None:
                value = []
            if not isinstance(value, list):
                raise RecordValueError(f"{definition_id} must be a list of record ids")
            # Deduped within the request itself -- so a same-request
            # [B, B] can never collide with itself even before a second,
            # concurrent request is involved (the real gate against THAT
            # is the composite unique constraint, see update_record).
            deduped: list = []
            for target_id in value:
                if target_id not in deduped:
                    deduped.append(target_id)
            m2m_data[definition_id] = deduped
        else:
            row_data[mapping.column] = value
    return row_data, m2m_data


def _translate_out(field_map: dict[str, _Mapping], row: dict, m2m_values: dict[str, list]) -> dict:
    reverse = {
        mapping.column: definition_id
        for definition_id, mapping in field_map.items()
        if isinstance(mapping, _ScalarField)
    }
    out = {reverse.get(name, name): value for name, value in row.items()}
    for definition_id in _m2m_mappings(field_map):
        out[definition_id] = m2m_values.get(definition_id, [])
    return out


def _translate_key(field_map: dict[str, _Mapping], key: str) -> str:
    if key == "id":
        return "id"
    mapping = field_map.get(key)
    if mapping is None:
        raise RecordValueError(f"unknown field or relationship: {key}")
    if isinstance(mapping, _ManyToManyField):
        raise RecordValueError(f"{key} cannot be used for filtering or sorting")
    return mapping.column


def _join_table_sql(join_table: DBTable) -> sql.Composable:
    return sql.SQL("{}.{}").format(
        sql.Identifier(join_table.tenant_database.schema_name), sql.Identifier(join_table.name)
    )


def _select_m2m_ids(join_table: DBTable, own_column: str, other_column: str, own_id) -> list:
    query = sql.SQL("SELECT {other} FROM {table} WHERE {own} = %s ORDER BY {other}").format(
        other=sql.Identifier(other_column), table=_join_table_sql(join_table), own=sql.Identifier(own_column)
    )
    with connections["tenant"].cursor() as cursor:
        cursor.execute(query, [own_id])
        return [row[0] for row in cursor.fetchall()]


def _select_m2m_ids_for_many(
    join_table: DBTable, own_column: str, other_column: str, own_ids: list
) -> dict:
    """Exactly one query per M:M relationship per page, never per row --
    list_records' own reason for keeping this separate from
    _select_m2m_ids above."""
    result: dict = {own_id: [] for own_id in own_ids}
    if not own_ids:
        return result
    query = sql.SQL(
        "SELECT {own}, {other} FROM {table} WHERE {own} = ANY(%s) ORDER BY {own}, {other}"
    ).format(
        own=sql.Identifier(own_column), other=sql.Identifier(other_column), table=_join_table_sql(join_table)
    )
    with connections["tenant"].cursor() as cursor:
        cursor.execute(query, [own_ids])
        for own_id, other_id in cursor.fetchall():
            result[own_id].append(other_id)
    return result


def _insert_m2m_rows(
    join_table: DBTable, own_column: str, other_column: str, own_id, other_ids: list
) -> None:
    if not other_ids:
        return
    query = sql.SQL("INSERT INTO {table} ({own}, {other}) VALUES {values}").format(
        table=_join_table_sql(join_table),
        own=sql.Identifier(own_column),
        other=sql.Identifier(other_column),
        values=sql.SQL(", ").join(sql.SQL("(%s, %s)") for _ in other_ids),
    )
    params = []
    for other_id in other_ids:
        params.extend([own_id, other_id])
    with connections["tenant"].cursor() as cursor:
        cursor.execute(query, params)


def _delete_m2m_rows(
    join_table: DBTable, own_column: str, other_column: str, own_id, other_ids: list
) -> None:
    if not other_ids:
        return
    query = sql.SQL("DELETE FROM {table} WHERE {own} = %s AND {other} = ANY(%s)").format(
        table=_join_table_sql(join_table), own=sql.Identifier(own_column), other=sql.Identifier(other_column)
    )
    with connections["tenant"].cursor() as cursor:
        cursor.execute(query, [own_id, other_ids])


def _read_m2m_values(field_map: dict[str, _Mapping], record_id) -> dict[str, list]:
    m2m = _m2m_mappings(field_map)
    if not m2m:
        return {}
    join_tables = _resolve_join_tables(m2m)
    return {
        definition_id: _select_m2m_ids(
            join_tables[mapping.join_table_id], mapping.own_column, mapping.other_column, record_id
        )
        for definition_id, mapping in m2m.items()
    }


def _run(fn):
    try:
        return fn()
    except RowValueError as exc:
        raise RecordValueError(str(exc)) from exc
    except DjangoIntegrityError as exc:
        # Django's own IntegrityError is one flat class covering both a
        # foreign-key violation (an existing message here, pre-dating
        # unique fields) and a unique-constraint violation (Post-Phase-3
        # Integration Enablement, Part 3) -- distinguished via the
        # original psycopg exception Django's DB wrapper chains as
        # __cause__, not by string-matching a message.
        if isinstance(exc.__cause__, psycopg_errors.UniqueViolation):
            raise RecordValueError("a record with this value already exists") from exc
        raise RecordValueError("referenced record does not exist") from exc
    except DjangoDatabaseError as exc:
        raise RecordValueError("invalid record data") from exc


def list_records(actor, model: ModelDefinition, *, limit, offset, ordering, filters, search) -> dict:
    receipt, table = resolve(actor, model, "database.read", action="app_instance.record.list")
    field_map = _field_map(receipt, model)

    physical_filters = {_translate_key(field_map, key): value for key, value in (filters or {}).items()}
    physical_ordering = None
    if ordering:
        desc = ordering.startswith("-")
        key = ordering[1:] if desc else ordering
        name = _translate_key(field_map, key)
        physical_ordering = f"-{name}" if desc else name

    result = _run(
        lambda: row_ops.list_rows(
            table=table, limit=limit, offset=offset, ordering=physical_ordering,
            filters=physical_filters, search=search,
        )
    )
    m2m = _m2m_mappings(field_map)
    if m2m:
        join_tables = _resolve_join_tables(m2m)
        own_ids = [row["id"] for row in result["results"]]
        # One query per M:M relationship for the whole page, never per row.
        per_relation = {
            definition_id: _select_m2m_ids_for_many(
                join_tables[mapping.join_table_id], mapping.own_column, mapping.other_column, own_ids
            )
            for definition_id, mapping in m2m.items()
        }
        result["results"] = [
            _translate_out(
                field_map,
                row,
                {definition_id: per_relation[definition_id].get(row["id"], []) for definition_id in m2m},
            )
            for row in result["results"]
        ]
    else:
        result["results"] = [_translate_out(field_map, row, {}) for row in result["results"]]
    return result


def get_record(actor, model: ModelDefinition, record_id) -> dict:
    receipt, table = resolve(actor, model, "database.read", action="app_instance.record.read")
    row = _run(lambda: row_ops.get_row(table, record_id))
    field_map = _field_map(receipt, model)
    return _translate_out(field_map, row, _read_m2m_values(field_map, record_id))


def create_record(actor, model: ModelDefinition, data: dict) -> dict:
    receipt, table = resolve(actor, model, "database.write", action="app_instance.record.create")
    field_map = _field_map(receipt, model)
    row_data, m2m_data = _translate_in(field_map, data)
    m2m = _m2m_mappings(field_map)
    join_tables = _resolve_join_tables(m2m)

    def _do():
        with transaction.atomic(using="tenant"):
            row = row_ops.insert_row(table, row_data)
            for definition_id, other_ids in m2m_data.items():
                mapping = m2m[definition_id]
                _insert_m2m_rows(
                    join_tables[mapping.join_table_id], mapping.own_column, mapping.other_column,
                    row["id"], other_ids,
                )
            return row

    row = _run(_do)
    event(actor, model, "record.create", row["id"])
    return _translate_out(field_map, row, _read_m2m_values(field_map, row["id"]))


def update_record(actor, model: ModelDefinition, record_id, data: dict) -> dict:
    receipt, table = resolve(actor, model, "database.write", action="app_instance.record.update")
    field_map = _field_map(receipt, model)
    row_data, m2m_data = _translate_in(field_map, data)
    m2m = _m2m_mappings(field_map)
    join_tables = _resolve_join_tables(m2m)

    def _do():
        with transaction.atomic(using="tenant"):
            row = (
                row_ops.update_row(table, record_id, row_data)
                if row_data
                else row_ops.get_row(table, record_id)
            )
            # A diff against current state, not a delete-everything-then-
            # reinsert -- inherently racy against a second concurrent
            # update of the same record/relationship, by design: the real
            # composite UNIQUE constraint on the join table (not this
            # diff) is the actual gate against a duplicate landing,
            # matching this project's "database constraint is the real
            # gate" discipline (see test_many_to_many.py's concurrency
            # test).
            for definition_id, desired_ids in m2m_data.items():
                mapping = m2m[definition_id]
                join_table = join_tables[mapping.join_table_id]
                current_ids = _select_m2m_ids(join_table, mapping.own_column, mapping.other_column, record_id)
                current_set, desired_set = set(current_ids), set(desired_ids)
                _delete_m2m_rows(
                    join_table, mapping.own_column, mapping.other_column, record_id,
                    list(current_set - desired_set),
                )
                _insert_m2m_rows(
                    join_table, mapping.own_column, mapping.other_column, record_id,
                    list(desired_set - current_set),
                )
            return row

    row = _run(_do)
    event(actor, model, "record.update", record_id, fields=sorted(data))
    return _translate_out(field_map, row, _read_m2m_values(field_map, record_id))


def delete_record(actor, model: ModelDefinition, record_id) -> None:
    _receipt, table = resolve(actor, model, "database.write", action="app_instance.record.delete")
    # Both join-table FK columns are physically ON DELETE CASCADE
    # (runtime_build._build_join_table / schema_evolution.
    # _add_join_table_to_runtime), so this plain base-row delete already
    # removes every M:M association referencing this record on both
    # sides -- no extra code needed here.
    _run(lambda: row_ops.delete_row(table, record_id))
    # Attachments live in the control-plane database; this is a second,
    # non-atomic step after the tenant-table delete already committed (same
    # documented limit as the rest of this module -- no distributed
    # atomicity claim). A crash between the two leaves orphaned attachment
    # rows pointing at a now-nonexistent record, not a dangling file byte:
    # the FileObject itself is untouched, only the association is meant to
    # go. Cheap to reconcile later (the record no longer exists to list them
    # against); not silently ignored, see THREAT_MODEL.md.
    RecordAttachment.objects.filter(model=model, record_id=record_id).delete()
    event(actor, model, "record.delete", record_id)


def event(actor, model: ModelDefinition, action, record_id, **context):
    audit.record(
        actor=actor,
        organization_id=model.instance.organization_id,
        action=f"app_instance.{action}",
        resource_type="app_model",
        resource_id=model.id,
        context={"record_id": str(record_id), **context},
    )
