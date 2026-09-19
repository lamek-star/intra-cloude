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

import uuid
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
from org_units.models import OrganizationalUnit
from permissions.services import has_permission

from . import operation_journal, quantity_ledger, unit_scope
from .access import RESOURCE_TYPE_APP_MODEL
from .models import FieldDefinition, ModelDefinition, RuntimeProvision
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


def _has_blanket_access(
    actor, model: ModelDefinition, receipt: RuntimeProvision, capability: str
) -> bool:
    """Whole-database or whole-model (Phase 7 "module scope") access --
    everything short of a unit-scoped grant, which only resolve_scoped()
    below falls back to."""
    instance = model.instance
    return has_permission(
        actor, capability, organization_id=instance.organization_id, resource=_resource(receipt.database_id)
    ) or has_permission(
        actor,
        capability,
        organization_id=instance.organization_id,
        resource=(RESOURCE_TYPE_APP_MODEL, model.id),
    )


def _require(actor, model: ModelDefinition, capability: str, *, action: str) -> RuntimeProvision:
    receipt = _receipt(model)
    if not _has_blanket_access(actor, model, receipt, capability):
        audit.record(
            actor=actor,
            organization_id=model.instance.organization_id,
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


def resolve_scoped(
    actor, model: ModelDefinition, capability: str, *, action: str
) -> tuple[RuntimeProvision, DBTable, set | None]:
    """Like resolve(), but when the actor lacks blanket (database- or
    module-scoped) access, falls back to a Phase 7 Step 3 unit-scoped
    grant and returns the set of unit ids access is restricted to instead
    of raising. `None` in the third slot means unrestricted (no row
    filtering needed) -- the same meaning list_records/get_record/etc.
    already give it. Used by every record CRUD function below; deliberately
    NOT used by attachments.py, which stays blanket-access-only for this
    pass (see docs/implementation/APP_PLATFORM_PHASE7.md's known limits)."""
    receipt = _receipt(model)
    if _has_blanket_access(actor, model, receipt, capability):
        return receipt, _table(receipt, model), None
    units = unit_scope.granted_unit_ids(actor, model, capability)
    if units:
        return receipt, _table(receipt, model), units
    audit.record(
        actor=actor,
        organization_id=model.instance.organization_id,
        action=action,
        resource_type="app_model",
        resource_id=model.id,
        result=AuditEvent.Result.DENIED,
    )
    raise RecordAccessDenied(f"{capability} required")


def record_exists(table: DBTable, record_id) -> bool:
    try:
        row_ops.get_row(table, record_id)
    except row_ops.RowNotFound:
        return False
    return True


def lock_record(table: DBTable, record_id) -> dict:
    """Read under a tenant row lock so authorization/conditions cannot race a write."""
    if not connections["tenant"].in_atomic_block:
        raise RuntimeError("Record locking requires a tenant transaction")
    with connections["tenant"].cursor() as cursor:
        cursor.execute(sql.SQL("SELECT id FROM {} WHERE id = %s FOR UPDATE").format(
            sql.Identifier(table.tenant_database.schema_name, table.name)
        ), [record_id])
        if cursor.fetchone() is None:
            raise row_ops.RowNotFound()
    return row_ops.get_row(table, record_id)


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


def _validate_org_unit_references(model: ModelDefinition, data: dict) -> None:
    """org_unit_reference is the one field type whose target row lives in a
    different Postgres database (the control plane) than the value being
    written (a per-tenant database) -- a real FK constraint is impossible
    across that boundary, so existence and organization-match are checked
    here explicitly, the same "validate before it reaches storage"
    discipline this codebase already applies wherever a real DB constraint
    can't cover a rule (e.g. definitions.py's own default_value/notify_url
    validation)."""
    reference_field_ids = {
        str(field_id)
        for field_id in model.fields.filter(
            data_type=FieldDefinition.DataType.ORG_UNIT_REFERENCE
        ).values_list("id", flat=True)
    }
    if not reference_field_ids:
        return
    for definition_id, value in data.items():
        if definition_id not in reference_field_ids or value is None:
            continue
        try:
            unit_id = uuid.UUID(str(value))
        except (ValueError, AttributeError, TypeError) as exc:
            raise RecordValueError(f"{definition_id}: not a valid organizational unit id") from exc
        if not OrganizationalUnit.objects.filter(
            id=unit_id, organization_id=model.instance.organization_id
        ).exists():
            raise RecordValueError(f"{definition_id}: no such organizational unit in this organization")


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
        if isinstance(exc.__cause__, psycopg_errors.CheckViolation):
            # A quantity_ledger.py-installed trigger's own RAISE EXCEPTION
            # (insufficient balance, or a direct write to a ledger-guarded
            # column/row) -- surfaced verbatim rather than the generic
            # "referenced record does not exist" below, which would be
            # actively misleading here.
            message = exc.__cause__.diag.message_primary or str(exc.__cause__)
            raise RecordValueError(message) from exc
        raise RecordValueError("referenced record does not exist") from exc
    except DjangoDatabaseError as exc:
        raise RecordValueError("invalid record data") from exc


def _unit_column(field_map: dict[str, _Mapping], model: ModelDefinition) -> tuple[str, str] | None:
    """(definition_id, physical column name) of the model's single
    org_unit_reference field, or None if it doesn't have exactly one --
    the same "unit scoping doesn't apply" case unit_scope.
    unit_reference_field already defines at grant-creation time."""
    field = unit_scope.unit_reference_field(model)
    if field is None:
        return None
    mapping = field_map.get(str(field.id))
    if not isinstance(mapping, _ScalarField):
        return None
    return str(field.id), mapping.column


def _apply_unit_scope_filter(
    physical_filters: dict, field_map: dict[str, _Mapping], model: ModelDefinition, granted_units: set
) -> dict:
    """Restricts a list query's filters to the actor's granted units.
    Overrides rather than intersects a caller-supplied filter on the same
    column -- documented in APP_PLATFORM_PHASE7.md as a known, deliberately
    accepted rough edge, never a way to see outside the granted scope."""
    unit_info = _unit_column(field_map, model)
    if unit_info is None:
        # No single org_unit_reference field to scope by -- a unit-scoped
        # grant on a model shaped like this can never match any record.
        # Reuses the real query path's own empty-IN-list handling (always
        # zero rows) rather than hand-building a matching result shape.
        return {**physical_filters, "id": []}
    _, unit_column = unit_info
    return {**physical_filters, unit_column: [str(unit_id) for unit_id in granted_units]}


def list_records(actor, model: ModelDefinition, *, limit, offset, ordering, filters, search) -> dict:
    receipt, table, granted_units = resolve_scoped(
        actor, model, "database.read", action="app_instance.record.list"
    )
    field_map = _field_map(receipt, model)

    physical_filters = {_translate_key(field_map, key): value for key, value in (filters or {}).items()}
    if granted_units is not None:
        physical_filters = _apply_unit_scope_filter(physical_filters, field_map, model, granted_units)
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


def _check_row_in_unit_scope(
    row: dict, field_map: dict[str, _Mapping], model: ModelDefinition, granted_units: set
) -> None:
    unit_info = _unit_column(field_map, model)
    value = row.get(unit_info[1]) if unit_info is not None else None
    # Values compared as strings, not raw UUID objects -- psycopg3 returns
    # a native uuid.UUID for a UUID column, while `granted_units` came from
    # a Django queryset (also UUID objects, but not guaranteed identical
    # instances/representation), so string comparison sidesteps any
    # cross-library type mismatch rather than assuming they match exactly.
    if value is None or str(value) not in {str(unit_id) for unit_id in granted_units}:
        raise RecordAccessDenied("record is outside your granted organizational unit")


def get_record(actor, model: ModelDefinition, record_id) -> dict:
    receipt, table, granted_units = resolve_scoped(
        actor, model, "database.read", action="app_instance.record.read"
    )
    row = _run(lambda: row_ops.get_row(table, record_id))
    field_map = _field_map(receipt, model)
    if granted_units is not None:
        _check_row_in_unit_scope(row, field_map, model, granted_units)
    return _translate_out(field_map, row, _read_m2m_values(field_map, record_id))


def _check_new_value_in_unit_scope(data: dict, model: ModelDefinition, granted_units: set) -> None:
    """A unit-scoped actor can only create/move a record into one of
    their own granted units -- can't create an unscoped record (no unit
    set at all) and can't assign a unit outside their grant."""
    field = unit_scope.unit_reference_field(model)
    value = data.get(str(field.id)) if field is not None else None
    if field is None or value is None or str(value) not in {str(unit_id) for unit_id in granted_units}:
        raise RecordAccessDenied("this record's organizational unit is outside your grant")


def create_record(actor, model: ModelDefinition, data: dict, *, idempotency_key=None) -> dict:
    receipt, table, granted_units = resolve_scoped(
        actor, model, "database.write", action="app_instance.record.create"
    )
    balance_model = quantity_ledger.balance_model_for_movement(model)
    if balance_model is not None:
        # A movement on a ledger-bound model changes that ledger's balance.
        resolve_scoped(actor, balance_model, "database.write", action="app_instance.record.create")
    if granted_units is not None:
        _check_new_value_in_unit_scope(data, model, granted_units)
    field_map = _field_map(receipt, model)
    _validate_org_unit_references(model, data)
    row_data, m2m_data = _translate_in(field_map, data)
    m2m = _m2m_mappings(field_map)
    join_tables = _resolve_join_tables(m2m)
    request_key, fingerprint = operation_journal.request_identity(actor, model, idempotency_key, data)

    def _do():
        with transaction.atomic(using="tenant"):
            replayed = operation_journal.replay(receipt, request_key, fingerprint)
            if replayed is not None:
                if granted_units is not None:
                    current = lock_record(table, replayed["id"])
                    _check_row_in_unit_scope(current, field_map, model, granted_units)
                return replayed
            row = row_ops.insert_row(table, row_data)
            for definition_id, other_ids in m2m_data.items():
                mapping = m2m[definition_id]
                _insert_m2m_rows(
                    join_tables[mapping.join_table_id], mapping.own_column, mapping.other_column,
                    row["id"], other_ids,
                )
            result = _translate_out(field_map, row, _read_m2m_values(field_map, row["id"]))
            operation_journal.append(
                receipt, actor, model, "record.create", row["id"],
                request_key=request_key, request_fingerprint=fingerprint, response=result,
            )
            return result

    return _run(_do)


def update_record(actor, model: ModelDefinition, record_id, data: dict) -> dict:
    receipt, table, granted_units = resolve_scoped(
        actor, model, "database.write", action="app_instance.record.update"
    )
    field_map = _field_map(receipt, model)
    if granted_units is not None:
        # The record's *current* unit must already be in scope (can't
        # touch a record outside your grant at all), and if this update
        # changes the unit, the *new* value must be in scope too (can't
        # move a record into, or out to, a unit outside your grant).
        unit_field = unit_scope.unit_reference_field(model)
        if unit_field is not None and str(unit_field.id) in data:
            _check_new_value_in_unit_scope(data, model, granted_units)
    _validate_org_unit_references(model, data)
    row_data, m2m_data = _translate_in(field_map, data)
    m2m = _m2m_mappings(field_map)
    join_tables = _resolve_join_tables(m2m)

    def _do():
        with transaction.atomic(using="tenant"):
            current_row = lock_record(table, record_id)
            if granted_units is not None:
                _check_row_in_unit_scope(current_row, field_map, model, granted_units)
            row = (
                row_ops.update_row(table, record_id, row_data)
                if row_data
                else row_ops.get_row(table, record_id)
            )
            # The base-row lock serializes relationship-set replacement.
            # The database UNIQUE constraint also protects raw join-table writes.
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
            operation_journal.append(receipt, actor, model, "record.update", record_id, fields=sorted(data))
            return row

    row = _run(_do)
    return _translate_out(field_map, row, _read_m2m_values(field_map, record_id))


def delete_record(actor, model: ModelDefinition, record_id) -> None:
    receipt, table, granted_units = resolve_scoped(
        actor, model, "database.write", action="app_instance.record.delete"
    )
    # Both join-table FK columns are physically ON DELETE CASCADE
    # (runtime_build._build_join_table / schema_evolution.
    # _add_join_table_to_runtime), so this plain base-row delete already
    # removes every M:M association referencing this record on both
    # sides -- no extra code needed here.
    def _do():
        with transaction.atomic(using="tenant"):
            current_row = lock_record(table, record_id)
            if granted_units is not None:
                _check_row_in_unit_scope(current_row, _field_map(receipt, model), model, granted_units)
            row_ops.delete_row(table, record_id)
            operation_journal.append(receipt, actor, model, "record.delete", record_id)

    _run(_do)
    # The durable journal replays attachment cleanup after tenant commit.


def event(actor, model: ModelDefinition, action, record_id, **context):
    audit.record(
        actor=actor,
        organization_id=model.instance.organization_id,
        action=f"app_instance.{action}",
        resource_type="app_model",
        resource_id=model.id,
        context={"record_id": str(record_id), **context},
    )

