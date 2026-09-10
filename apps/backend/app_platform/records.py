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

from django.db import Error as DjangoDatabaseError
from django.db import IntegrityError as DjangoIntegrityError
from django.http import Http404
from psycopg import errors as psycopg_errors

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


def _field_map(model: ModelDefinition) -> dict[str, str]:
    """definition id (str) -> physical column name, covering this model's
    own fields plus its outgoing relationships (both are real columns on
    its table; incoming relationships live on the *other* model's table)."""
    mapping = {str(field.id): physical_name("f", str(field.id)) for field in model.fields.all()}
    mapping.update({str(rel.id): physical_name("r", str(rel.id)) for rel in model.outgoing.all()})
    return mapping


def _translate_in(field_map: dict[str, str], data: dict) -> dict:
    if not isinstance(data, dict):
        raise RecordValueError("expected an object")
    physical = {}
    for definition_id, value in data.items():
        name = field_map.get(definition_id)
        if name is None:
            raise RecordValueError(f"unknown field or relationship: {definition_id}")
        physical[name] = value
    return physical


def _translate_out(field_map: dict[str, str], row: dict) -> dict:
    reverse = {name: definition_id for definition_id, name in field_map.items()}
    return {reverse.get(name, name): value for name, value in row.items()}


def _translate_key(field_map: dict[str, str], key: str) -> str:
    if key == "id":
        return "id"
    name = field_map.get(key)
    if name is None:
        raise RecordValueError(f"unknown field or relationship: {key}")
    return name


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
    _receipt, table = resolve(actor, model, "database.read", action="app_instance.record.list")
    field_map = _field_map(model)

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
    result["results"] = [_translate_out(field_map, row) for row in result["results"]]
    return result


def get_record(actor, model: ModelDefinition, record_id) -> dict:
    _receipt, table = resolve(actor, model, "database.read", action="app_instance.record.read")
    row = _run(lambda: row_ops.get_row(table, record_id))
    return _translate_out(_field_map(model), row)


def create_record(actor, model: ModelDefinition, data: dict) -> dict:
    _receipt, table = resolve(actor, model, "database.write", action="app_instance.record.create")
    field_map = _field_map(model)
    physical_data = _translate_in(field_map, data)
    row = _run(lambda: row_ops.insert_row(table, physical_data))
    event(actor, model, "record.create", row["id"])
    return _translate_out(field_map, row)


def update_record(actor, model: ModelDefinition, record_id, data: dict) -> dict:
    _receipt, table = resolve(actor, model, "database.write", action="app_instance.record.update")
    field_map = _field_map(model)
    physical_data = _translate_in(field_map, data)
    row = _run(lambda: row_ops.update_row(table, record_id, physical_data))
    event(actor, model, "record.update", record_id, fields=sorted(data))
    return _translate_out(field_map, row)


def delete_record(actor, model: ModelDefinition, record_id) -> None:
    _receipt, table = resolve(actor, model, "database.write", action="app_instance.record.delete")
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
