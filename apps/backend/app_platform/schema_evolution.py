"""Additive-only live schema changes against an already-provisioned,
possibly populated runtime (Phase 3 step 3).

Deliberately narrow, per the roadmap: a brand-new model, field, or
relationship only. Never a rename, type change, deletion, or any edit to
something that already exists physically -- those stay blocked by
`instances.lock_active` exactly as before this step, since none of them
can be done safely without a real migration strategy this phase doesn't
build. Reuses the exact validated `databases.services` DDL operations
Phase 2's own provisioning uses (`allow_managed_schema=True` is the one
sanctioned way past their normal "this schema belongs to an app" guard —
see that parameter's own docstring), inside the same tenant-transaction
discipline `provisioning.execute` established.

Only `RuntimeProvision.bindings` is extended here, never `.plan` -- the
0004 migration's own `app_platform_identity_guard` trigger makes `plan`
unconditionally immutable after creation (by design: it's the frozen
record of exactly what the original provisioning fingerprint produced).
`bindings` carries no such constraint and is exactly what
`records.resolve`/`_table` actually read to find a model's physical
table, so extending only it is both sufficient and the only option.
"""

from django.db import connection, connections
from psycopg import sql
from rest_framework.exceptions import ValidationError

from databases import services
from databases.models import DBColumn, DBForeignKey, DBTable
from databases.services import SchemaValidationError

from .access import check, require_manage
from .models import (
    ConstraintDefinition,
    FieldDefinition,
    ModelDefinition,
    RelationshipDefinition,
    RuntimeProvision,
)
from .runtime_plan import physical_name


def require_addition(actor, instance) -> None:
    """The extra bar a *live* schema change must clear beyond ordinary
    metadata editing (`access.require_manage`): org-wide
    `database.schema.manage`, the same capability provisioning itself
    requires — a schema-only app grant must not be enough to trigger real
    tenant DDL, matching PERMISSIONS.md's existing provisioning rule."""
    require_manage(actor, instance)
    check(actor, instance.organization_id, "database.schema.manage")


def mark_addition_transaction() -> None:
    """Announces to the 0007 migration's control-plane trigger that the
    definition row about to be INSERTed in *this* transaction is this
    module's own sanctioned, capability-checked addition -- not some other
    code path bypassing it. `SET LOCAL` is transaction-scoped and resets
    itself on commit/rollback, so this can never leak into an unrelated
    request. Call only after `require_addition` has already succeeded."""
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL app_platform.schema_evolution = 'on'")


def ready_receipt(instance) -> RuntimeProvision | None:
    """None if this instance has never been provisioned (pure metadata
    edit, unchanged pre-Phase-3-step-3 behavior). Raises if a receipt
    exists but hasn't finished (or failed) provisioning yet -- mutating
    definitions while that's unresolved isn't safe to reason about."""
    receipt = RuntimeProvision.objects.select_for_update().filter(instance=instance).first()
    if receipt is None:
        return None
    if not receipt.completed_at:
        raise ValidationError(
            "Runtime provisioning is in progress or failed; resolve it before editing definitions."
        )
    return receipt


def _table_for(receipt: RuntimeProvision, model: ModelDefinition) -> DBTable:
    table_id = receipt.bindings.get("models", {}).get(str(model.id))
    if table_id is None:
        raise ValidationError("This model's runtime table could not be found.")
    return DBTable.objects.select_related("tenant_database").get(pk=table_id)


def _table_has_rows(table: DBTable) -> bool:
    with connections["tenant"].cursor() as cursor:
        cursor.execute(
            sql.SQL("SELECT EXISTS (SELECT 1 FROM {}.{})").format(
                sql.Identifier(table.tenant_database.schema_name), sql.Identifier(table.name)
            )
        )
        return bool(cursor.fetchone()[0])


def add_model_to_runtime(receipt: RuntimeProvision, model: ModelDefinition, actor) -> DBTable:
    # receipt.database is only nullable pre-completion (the model's own
    # CheckConstraint enforces this); ready_receipt() only ever returns a
    # receipt with completed_at set, so this is always populated here.
    assert receipt.database is not None
    table = services.create_table(
        actor=actor,
        tenant_database=receipt.database,
        name=physical_name("m", str(model.id)),
        allow_managed_schema=True,
    )
    receipt.bindings.setdefault("models", {})[str(model.id)] = str(table.id)
    receipt.save(update_fields=["bindings"])
    return table


def add_field_to_runtime(receipt: RuntimeProvision, field: FieldDefinition, actor) -> None:
    model = field.model
    table = _table_for(receipt, model)
    if field.required and field.default_value is None and _table_has_rows(table):
        raise ValidationError(
            "This model already has records -- a new required field needs a default value "
            "to add safely (existing rows would otherwise be left with no value)."
        )
    try:
        column = services.add_column(
            actor=actor,
            table=table,
            name=physical_name("f", str(field.id)),
            data_type=field.data_type,
            is_nullable=not field.required,
            precision=18 if field.data_type == "decimal" else None,
            scale=4 if field.data_type == "decimal" else None,
            default_value=field.default_value,
            is_unique=field.unique,
            is_indexed=field.indexed,
            allow_managed_schema=True,
        )
    except SchemaValidationError as exc:
        # Most likely: a brand-new unique field with a default_value on a
        # model that already has 2+ rows -- every existing row would get
        # the same default, violating uniqueness. add_column's own DDL
        # already rolled back in full (see its docstring); this is
        # surfacing that clean rejection through the API, not catching a
        # partial failure.
        raise ValidationError(str(exc)) from exc
    receipt.bindings.setdefault("fields", {})[str(field.id)] = str(column.id)
    receipt.save(update_fields=["bindings"])


def _column_for(receipt: RuntimeProvision, field: FieldDefinition) -> DBColumn:
    column_id = receipt.bindings.get("fields", {}).get(str(field.id))
    if column_id is None:
        raise ValidationError("This field's runtime column could not be found.")
    return DBColumn.objects.select_related("table__tenant_database").get(pk=column_id)


def set_field_unique(receipt: RuntimeProvision, field: FieldDefinition, actor) -> None:
    """Retrofits a UNIQUE constraint onto a field that was already
    live-added without one -- the populated-runtime half of Post-Phase-3
    Integration Enablement's uniqueness requirement (the not-yet-
    provisioned case is just a metadata edit, handled by instances.py
    without ever reaching here). Idempotent (services.add_unique_constraint
    itself is); a genuine duplicate-value conflict surfaces as a clean
    ValidationError, with the existing data completely untouched -- see
    that function's own docstring for why."""
    column = _column_for(receipt, field)
    try:
        services.add_unique_constraint(actor=actor, column=column, allow_managed_schema=True)
    except SchemaValidationError as exc:
        raise ValidationError(str(exc)) from exc
    if not field.unique:
        field.unique = True
        field.save(update_fields=["unique"])


def set_field_indexed(receipt: RuntimeProvision, field: FieldDefinition, actor) -> None:
    """Retrofits a plain (non-unique) B-tree index onto a field that was
    already live-added without one. See set_field_unique above -- same
    reasoning, no uniqueness constraint so nothing to reject."""
    column = _column_for(receipt, field)
    try:
        services.add_index(actor=actor, column=column, allow_managed_schema=True)
    except SchemaValidationError as exc:
        raise ValidationError(str(exc)) from exc
    if not field.indexed:
        field.indexed = True
        field.save(update_fields=["indexed"])


def add_constraint_to_runtime(receipt: RuntimeProvision, constraint: ConstraintDefinition, actor) -> None:
    """Retrofits a composite UNIQUE constraint onto an already-provisioned
    model -- the live-addition counterpart to fresh provisioning's own
    per-model constraint loop in runtime_build.build(). Idempotent like
    add_model_to_runtime/add_field_to_runtime/add_relationship_to_runtime
    above (services.add_field_set_unique_constraint itself is, keyed by
    this constraint's own stable id); a genuine duplicate-combination
    conflict surfaces as a clean ValidationError with the existing data
    completely untouched -- see that function's own docstring for why
    (ADD CONSTRAINT is one statement inside one transaction)."""
    table = _table_for(receipt, constraint.model)
    columns = [_column_for(receipt, field) for field in constraint.fields.all()]
    try:
        index = services.add_field_set_unique_constraint(
            actor=actor,
            table=table,
            columns=columns,
            constraint_id=constraint.id,
            allow_managed_schema=True,
        )
    except SchemaValidationError as exc:
        raise ValidationError(str(exc)) from exc
    receipt.bindings.setdefault("constraints", {})[str(constraint.id)] = str(index.id)
    receipt.save(update_fields=["bindings"])


def add_relationship_to_runtime(receipt: RuntimeProvision, relation: RelationshipDefinition, actor) -> None:
    source_table = _table_for(receipt, relation.source_model)
    target_table = _table_for(receipt, relation.target_model)
    if relation.kind == "many_to_many":
        receipt.bindings.setdefault("relationships", {})[str(relation.id)] = _add_join_table_to_runtime(
            receipt, relation, actor, source_table, target_table
        )
        receipt.save(update_fields=["bindings"])
        return
    column = services.add_column(
        actor=actor,
        table=source_table,
        name=physical_name("r", str(relation.id)),
        data_type="uuid",
        is_nullable=True,
        allow_managed_schema=True,
    )
    foreign_key = services.add_foreign_key(
        actor=actor,
        column=column,
        references_table=target_table,
        references_column=target_table.columns.get(is_primary_key=True),
        on_delete=relation.deletion_policy,
        allow_managed_schema=True,
    )
    receipt.bindings.setdefault("relationships", {})[str(relation.id)] = {
        "kind": "many_to_one",
        "column": str(column.id),
        "foreign_key": str(foreign_key.id),
    }
    receipt.save(update_fields=["bindings"])


def _add_join_table_to_runtime(receipt, relation, actor, source_table, target_table) -> dict:
    """Live-addition counterpart to runtime_build._build_join_table --
    deliberately duplicated rather than shared, matching the many_to_one
    path's own existing precedent above (also duplicated between this
    module and runtime_build.py): this module recomputes physical names
    locally instead of reading a stored plan, since a live addition was
    never part of the original plan/fingerprint in the first place."""
    join_table = services.create_table(
        actor=actor,
        tenant_database=receipt.database,
        name=physical_name("j", str(relation.id)),
        allow_managed_schema=True,
    )
    source_column = services.add_column(
        actor=actor,
        table=join_table,
        name="source_id",
        data_type="uuid",
        is_nullable=False,
        allow_managed_schema=True,
    )
    target_column = services.add_column(
        actor=actor,
        table=join_table,
        name="target_id",
        data_type="uuid",
        is_nullable=False,
        allow_managed_schema=True,
    )
    source_fk = services.add_foreign_key(
        actor=actor,
        column=source_column,
        references_table=source_table,
        references_column=source_table.columns.get(is_primary_key=True),
        on_delete=DBForeignKey.OnDelete.CASCADE,
        allow_managed_schema=True,
    )
    target_fk = services.add_foreign_key(
        actor=actor,
        column=target_column,
        references_table=target_table,
        references_column=target_table.columns.get(is_primary_key=True),
        on_delete=DBForeignKey.OnDelete.CASCADE,
        allow_managed_schema=True,
    )
    unique_index = services.add_composite_unique_constraint(
        actor=actor,
        table=join_table,
        column_a=source_column,
        column_b=target_column,
        allow_managed_schema=True,
    )
    target_index = services.add_index(actor=actor, column=target_column, allow_managed_schema=True)
    return {
        "kind": "many_to_many",
        "join_table": str(join_table.id),
        "source_column": str(source_column.id),
        "target_column": str(target_column.id),
        "source_foreign_key": str(source_fk.id),
        "target_foreign_key": str(target_fk.id),
        "unique_index": str(unique_index.id),
        "target_index": str(target_index.id),
    }
