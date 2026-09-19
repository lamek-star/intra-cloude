"""ADR-0016's closing half: an opt-in, generic integer quantity ledger.

Administrator-bound mapping between an append-only movement model's field
and the balance model's field its inserts must atomically maintain, over a
shared set of relationship "dimensions" (e.g. Part, Warehouse). Installed
as real Postgres triggers on an already-provisioned, still-empty pair of
tables -- the operation stays atomic and concurrency-safe even for a
direct SQL insert/update that never goes through records.py, because
enforcement lives in the tenant database itself, not application code (the
same "the database is the real gate" discipline this codebase already
applies to composite uniqueness -- see ConstraintDefinition's own
docstring). operation_journal.py covers durable audit/webhook evidence for
a mutation that already committed; this covers making the mutation itself
atomic -- and rejecting an insufficient balance -- in the first place.
Never a second business datastore and never exposed through ordinary
table browsing beyond the two models an administrator already declared.
"""

from typing import NamedTuple

from django.db import connections, transaction
from psycopg import sql
from rest_framework import serializers

from databases.identifiers import validate_identifier

from . import instances, schema_evolution
from .access import require_manage
from .definitions import StrictSerializer, validate_definition
from .models import (
    AppInstance,
    FieldDefinition,
    ModelDefinition,
    QuantityLedgerBinding,
    QuantityLedgerDimension,
    RelationshipDefinition,
    RuntimeProvision,
)

# Transaction-local (SET LOCAL semantics via set_config(..., true)) flag the
# installed balance-table guard trigger checks before allowing a direct
# write to a guarded column. Only the movement-side trigger below ever sets
# it, and only for the duration of its own single upsert statement.
_LEDGER_WRITE_FLAG = "app_platform.ledger_write"

# Standard SQLSTATE for check_violation -- Django's DB wrapper maps SQLSTATE
# class 23 (integrity constraint violation) to IntegrityError, which
# records.py's _run() already distinguishes by the chained psycopg
# exception rather than by string-matching a message.
_CHECK_VIOLATION = "23514"


class DimensionInput(StrictSerializer):
    balance_relationship_id = serializers.UUIDField()
    movement_relationship_id = serializers.UUIDField()


class QuantityLedgerBindingInput(StrictSerializer):
    balance_model_id = serializers.UUIDField()
    balance_field_id = serializers.UUIDField()
    movement_model_id = serializers.UUIDField()
    movement_field_id = serializers.UUIDField()
    # A ledger's balance is keyed by a composite UNIQUE constraint over its dimensions,
    # and definitions.py requires at least two members for any constraint.
    dimensions = serializers.ListField(child=DimensionInput(), min_length=2, max_length=8)  # type: ignore[assignment]
    allow_negative = serializers.BooleanField(default=False)  # type: ignore[assignment]


def _model(instance, model_id, label) -> ModelDefinition:
    try:
        return instance.models.get(pk=model_id)
    except ModelDefinition.DoesNotExist as exc:
        raise serializers.ValidationError({label: "Must be a model on this instance."}) from exc


def _integer_field(model, field_id, label) -> FieldDefinition:
    try:
        field = model.fields.get(pk=field_id)
    except FieldDefinition.DoesNotExist as exc:
        raise serializers.ValidationError({label: "Must be a field on the given model."}) from exc
    if field.data_type != FieldDefinition.DataType.INTEGER or not field.required:
        raise serializers.ValidationError(
            {label: "Must be a required integer field -- this is a generic integer ledger."}
        )
    return field


def _dimension_relationship(model, relationship_id, label) -> RelationshipDefinition:
    try:
        return model.outgoing.get(pk=relationship_id, kind="many_to_one")
    except RelationshipDefinition.DoesNotExist as exc:
        raise serializers.ValidationError(
            {label: "Must be a many-to-one relationship owned by the given model."}
        ) from exc


def _matching_constraint(balance_model, balance_relationship_ids):
    """The composite UNIQUE constraint the installed trigger's `ON
    CONFLICT` target relies on -- must cover exactly this binding's
    dimensions and nothing else (see QuantityLedgerBinding's own
    docstring for why an extra scalar field would break the upsert)."""
    wanted = set(balance_relationship_ids)
    for constraint in balance_model.constraints.prefetch_related("fields", "relationships"):
        if not constraint.fields.exists() and {r.id for r in constraint.relationships.all()} == wanted:
            return constraint
    raise serializers.ValidationError(
        "balance_model needs an existing composite UNIQUE constraint over exactly these dimension "
        "relationships, and no scalar fields, before it can back a quantity ledger."
    )


def bind(actor, instance: AppInstance, data) -> QuantityLedgerBinding:
    """Binds a movement model's field to a balance model's field over a
    set of shared dimensions, and installs the real trigger that makes
    every future movement insert atomically maintain the balance.
    Requires an already-completed RuntimeProvision (there is no physical
    table to attach a trigger to before that) and requires both tables to
    still be empty -- existing business data is never silently reconciled
    or rewritten (ADR-0016)."""
    require_manage(actor, instance)
    values = instances.validated(QuantityLedgerBindingInput, data)

    with transaction.atomic():
        instance = instances._lock_instance(instance)
        receipt = schema_evolution.ready_receipt(instance)
        if receipt is None:
            raise serializers.ValidationError(
                "Provision this instance's runtime before binding a quantity ledger."
            )
        return _bind_locked(actor, instance, receipt, values)


def balance_model_for_movement(model: ModelDefinition) -> ModelDefinition | None:
    """The balance model a movement model's inserts change, if it is bound.
    Creating such a movement changes that balance, so the actor also needs
    write authority over the balance model (ADR-0016: "authority over
    affected balance and movement models") -- checked by records.create_record."""
    binding = (
        QuantityLedgerBinding.objects.filter(movement_model=model).select_related("balance_model").first()
    )
    return binding.balance_model if binding else None


def bind_declared(actor, instance: AppInstance, receipt: RuntimeProvision) -> list[QuantityLedgerBinding]:
    """Applies the `quantity_ledgers` its template version declared (if any),
    called by provisioning.execute inside its own transaction right after the
    physical runtime is built -- the one moment both tables are guaranteed
    empty. The declaration references the template's own definition ids;
    they are mapped to this instance's rows through `source_definition_id`.
    A declaration that no longer resolves fails provisioning loudly rather
    than leaving an instance whose stock silently has no ledger. A later
    template version that adds a declaration is NOT applied to an already-
    provisioned instance (its tables may hold data): use `bind()` explicitly."""
    version = instance.source_version
    if version is None:
        return []
    declared = validate_definition(version.definition).get("quantity_ledgers", [])
    if not declared:
        return []
    relationships = {
        str(r.source_definition_id): r
        for r in RelationshipDefinition.objects.filter(instance=instance, source_definition_id__isnull=False)
    }
    bindings = []
    for item in declared:
        balance_field = FieldDefinition.objects.get(
            model__instance=instance, source_definition_id=item["balance_field"]
        )
        movement_field = FieldDefinition.objects.get(
            model__instance=instance, source_definition_id=item["movement_field"]
        )
        values = {
            "balance_model_id": balance_field.model_id,
            "balance_field_id": balance_field.id,
            "movement_model_id": movement_field.model_id,
            "movement_field_id": movement_field.id,
            "dimensions": [
                {
                    "balance_relationship_id": relationships[pair["balance_relationship"]].id,
                    "movement_relationship_id": relationships[pair["movement_relationship"]].id,
                }
                for pair in item["dimensions"]
            ],
            "allow_negative": item["allow_negative"],
        }
        bindings.append(_bind_locked(actor, instance, receipt, values))
    return bindings


def _bind_locked(actor, instance: AppInstance, receipt: RuntimeProvision, values) -> QuantityLedgerBinding:
    """The validated core of bind(); the caller holds the instance lock and a
    ready receipt inside an open transaction."""
    schema_evolution.require_addition(actor, instance)
    schema_evolution.mark_addition_transaction()

    balance_model = _model(instance, values["balance_model_id"], "balance_model_id")
    movement_model = _model(instance, values["movement_model_id"], "movement_model_id")
    if balance_model.id == movement_model.id:
        raise serializers.ValidationError("balance_model_id and movement_model_id must differ.")
    balance_field = _integer_field(balance_model, values["balance_field_id"], "balance_field_id")
    if balance_field.default_value != 0:
        raise serializers.ValidationError(
            {"balance_field_id": "A ledger-backed balance field must default to 0."}
        )
    movement_field = _integer_field(movement_model, values["movement_field_id"], "movement_field_id")

    dimensions = []
    for item in values["dimensions"]:
        balance_relationship = _dimension_relationship(
            balance_model, item["balance_relationship_id"], "dimensions"
        )
        movement_relationship = _dimension_relationship(
            movement_model, item["movement_relationship_id"], "dimensions"
        )
        if balance_relationship.target_model_id != movement_relationship.target_model_id:
            raise serializers.ValidationError(
                {"dimensions": "Each pair must target the same model on both sides."}
            )
        dimensions.append((balance_relationship, movement_relationship))
    if len({r.id for r, _ in dimensions}) != len(dimensions) or len({r.id for _, r in dimensions}) != len(
        dimensions
    ):
        raise serializers.ValidationError({"dimensions": "A relationship cannot be repeated."})

    constraint = _matching_constraint(balance_model, [r.id for r, _ in dimensions])

    if QuantityLedgerBinding.objects.filter(
        balance_model=balance_model, balance_field=balance_field
    ).exists():
        raise serializers.ValidationError(
            {"balance_field_id": "This field is already bound to a quantity ledger."}
        )
    if QuantityLedgerBinding.objects.filter(
        movement_model=movement_model, movement_field=movement_field
    ).exists():
        raise serializers.ValidationError(
            {"movement_field_id": "This field is already bound to a quantity ledger."}
        )

    balance_table = schema_evolution._table_for(receipt, balance_model)
    movement_table = schema_evolution._table_for(receipt, movement_model)
    if schema_evolution._table_has_rows(balance_table) or schema_evolution._table_has_rows(movement_table):
        raise serializers.ValidationError(
            "Both models must still be empty -- existing business data is never silently "
            "reconciled into a new quantity ledger."
        )

    binding = QuantityLedgerBinding.objects.create(
        instance=instance,
        balance_model=balance_model,
        balance_field=balance_field,
        unique_constraint=constraint,
        movement_model=movement_model,
        movement_field=movement_field,
        allow_negative=values["allow_negative"],
        created_by=actor,
    )
    QuantityLedgerDimension.objects.bulk_create(
        QuantityLedgerDimension(
            binding=binding, balance_relationship=balance_rel, movement_relationship=movement_rel
        )
        for balance_rel, movement_rel in dimensions
    )
    with transaction.atomic(using="tenant"):
        _install(receipt, binding)
    instances.event(actor, instance, "quantity_ledger.bind", binding.id)
    return binding


class _Physical(NamedTuple):
    """Resolved physical tenant-schema names for one binding -- resolved
    through the receipt's own bindings, never re-derived by hand."""

    schema: sql.Identifier
    balance_tbl: sql.Identifier
    movement_tbl: sql.Identifier
    balance_col: sql.Identifier
    movement_col: sql.Identifier
    balance_dims: list[sql.Identifier]
    movement_dims: list[sql.Identifier]


def _physical(receipt, binding: QuantityLedgerBinding) -> _Physical:
    balance_table = schema_evolution._table_for(receipt, binding.balance_model)
    movement_table = schema_evolution._table_for(receipt, binding.movement_model)
    dims = list(binding.dimensions.select_related("balance_relationship", "movement_relationship"))
    return _Physical(
        schema=sql.Identifier(balance_table.tenant_database.schema_name),
        balance_tbl=sql.Identifier(balance_table.name),
        movement_tbl=sql.Identifier(movement_table.name),
        balance_col=sql.Identifier(schema_evolution._column_for(receipt, binding.balance_field).name),
        movement_col=sql.Identifier(schema_evolution._column_for(receipt, binding.movement_field).name),
        balance_dims=[
            sql.Identifier(schema_evolution._column_for_relationship(receipt, d.balance_relationship).name)
            for d in dims
        ],
        movement_dims=[
            sql.Identifier(schema_evolution._column_for_relationship(receipt, d.movement_relationship).name)
            for d in dims
        ],
    )


def _any(template: str, columns: list[sql.Identifier]) -> sql.Composable:
    return sql.SQL(" OR ").join(sql.SQL(template).format(c=column) for column in columns)


def _raise(message: str) -> sql.Composable:
    return sql.SQL("RAISE EXCEPTION {message} USING ERRCODE = {errcode}; ").format(
        message=sql.Literal(message), errcode=sql.Literal(_CHECK_VIOLATION)
    )


def _install(receipt, binding: QuantityLedgerBinding) -> None:
    phys = _physical(receipt, binding)
    schema, balance_tbl, movement_tbl = phys.schema, phys.balance_tbl, phys.movement_tbl
    balance_col, movement_col = phys.balance_col, phys.movement_col
    constraint_name = sql.Identifier(validate_identifier(f"idx_{binding.unique_constraint_id.hex}"))
    flag = sql.Literal(_LEDGER_WRITE_FLAG)
    hexid = binding.id.hex

    def name(prefix: str) -> sql.Identifier:
        return sql.Identifier(validate_identifier(f"{prefix}_{hexid}"))

    movement_fn, movement_trigger = name("ledger_mv"), name("trg_ledger_mv")
    movement_guard_fn, movement_guard_trigger = name("ledger_mvg"), name("trg_ledger_mvg")
    balance_fn, balance_trigger = name("ledger_bal"), name("trg_ledger_bal")
    truncate_fn = name("ledger_trc")
    truncate_mv_trigger, truncate_bal_trigger = name("trg_ledger_trc_mv"), name("trg_ledger_trc_bal")

    insert_columns = sql.SQL(", ").join([*phys.balance_dims, balance_col])
    insert_values = sql.SQL(", ").join(
        [*(sql.SQL("NEW.{}").format(c) for c in phys.movement_dims), sql.SQL("NEW.{}").format(movement_col)]
    )
    negative_guard = (
        sql.SQL("")
        if binding.allow_negative
        else sql.SQL(
            "IF new_balance < 0 THEN "
            "RAISE EXCEPTION {message}, new_balance USING ERRCODE = {errcode}; END IF; "
        ).format(
            message=sql.Literal("this quantity ledger balance would go negative (%)"),
            errcode=sql.Literal(_CHECK_VIOLATION),
        )
    )

    # AFTER INSERT on the movement table: upsert the matching balance row
    # (INSERT ... ON CONFLICT ON CONSTRAINT <the dimension's own composite
    # UNIQUE constraint> DO UPDATE) inside the same statement/transaction
    # as the movement insert that fired this trigger -- a crash or a raised
    # exception here rolls back the movement insert too, there is no
    # window where one commits without the other. Every dimension must be
    # set: relationship columns are nullable, and NULLs never conflict on a
    # UNIQUE constraint, so a NULL dimension would silently create an
    # orphan balance row per movement instead of updating a real one.
    # set_config(..., true) is transaction-local (SET LOCAL semantics) and
    # reset immediately after the single upsert it exists to authorize.
    movement_fn_ddl = sql.SQL(
        "CREATE FUNCTION {schema}.{fn}() RETURNS trigger AS $ledger$ "
        "DECLARE new_balance integer; "
        "BEGIN "
        "IF {any_null} THEN {null_error}END IF; "
        "PERFORM set_config({flag}, 'on', true); "
        "INSERT INTO {schema}.{balance_tbl} ({insert_cols}) VALUES ({insert_vals}) "
        "ON CONFLICT ON CONSTRAINT {constraint} DO UPDATE SET {balance_col} = "
        "{balance_tbl}.{balance_col} + EXCLUDED.{balance_col} "
        "RETURNING {balance_col} INTO new_balance; "
        "PERFORM set_config({flag}, 'off', true); "
        "{negative_guard}"
        "RETURN NEW; "
        "END; $ledger$ LANGUAGE plpgsql"
    ).format(
        schema=schema,
        fn=movement_fn,
        any_null=_any("NEW.{c} IS NULL", phys.movement_dims),
        null_error=_raise("every dimension of a quantity ledger movement must be set"),
        flag=flag,
        balance_tbl=balance_tbl,
        insert_cols=insert_columns,
        insert_vals=insert_values,
        constraint=constraint_name,
        balance_col=balance_col,
        negative_guard=negative_guard,
    )
    movement_trigger_ddl = sql.SQL(
        "CREATE TRIGGER {trigger} AFTER INSERT ON {schema}.{movement_tbl} "
        "FOR EACH ROW EXECUTE FUNCTION {schema}.{fn}()"
    ).format(trigger=movement_trigger, schema=schema, movement_tbl=movement_tbl, fn=movement_fn)

    # BEFORE UPDATE/DELETE on the movement table: a movement is append-only.
    # Editing its quantity or dimensions, or deleting it, would change the
    # movement sum without changing the balance -- silent drift. A mistake
    # is corrected by recording a reversing movement (ADR-0016). Every
    # other column on the movement (a note, a reference) stays editable.
    movement_guard_fn_ddl = sql.SQL(
        "CREATE FUNCTION {schema}.{fn}() RETURNS trigger AS $ledger$ "
        "BEGIN "
        "IF TG_OP = 'DELETE' THEN {delete_error}END IF; "
        "IF {changed} THEN {edit_error}END IF; "
        "RETURN NEW; "
        "END; $ledger$ LANGUAGE plpgsql"
    ).format(
        schema=schema,
        fn=movement_guard_fn,
        delete_error=_raise(
            "ledger movements are append-only and cannot be deleted; record a reversing movement instead"
        ),
        changed=_any("NEW.{c} IS DISTINCT FROM OLD.{c}", [movement_col, *phys.movement_dims]),
        edit_error=_raise(
            "ledger movements are append-only and cannot be edited; record a reversing movement instead"
        ),
    )
    movement_guard_trigger_ddl = sql.SQL(
        "CREATE TRIGGER {trigger} BEFORE UPDATE OR DELETE ON {schema}.{movement_tbl} "
        "FOR EACH ROW EXECUTE FUNCTION {schema}.{fn}()"
    ).format(trigger=movement_guard_trigger, schema=schema, movement_tbl=movement_tbl, fn=movement_guard_fn)

    # BEFORE INSERT/UPDATE/DELETE on the balance table: reject any direct
    # write to the guarded column or its dimensions (or any delete of the
    # row at all) that didn't come from the movement trigger's own upsert
    # -- "prohibit bypass edits" from ADR-0016's own decision. The bypass
    # requires BOTH the transaction-local flag AND pg_trigger_depth() > 1,
    # i.e. that this statement was issued from inside another trigger: a
    # session that merely runs set_config(...) itself is at depth 1 and is
    # still rejected. (A role able to DDL -- ALTER TABLE ... DISABLE
    # TRIGGER, CREATE TRIGGER -- can always defeat any trigger; that
    # residual limit is documented, and reconcile() detects the drift.)
    # Every other column stays freely editable.
    balance_fn_ddl = sql.SQL(
        "CREATE FUNCTION {schema}.{fn}() RETURNS trigger AS $ledger$ "
        "BEGIN "
        "IF pg_trigger_depth() > 1 AND current_setting({flag}, true) IS NOT DISTINCT FROM 'on' THEN "
        "IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; RETURN NEW; END IF; "
        "IF TG_OP = 'DELETE' THEN {delete_error}"
        "ELSIF TG_OP = 'INSERT' THEN "
        "IF NEW.{balance_col} <> 0 THEN {insert_error}END IF; "
        "ELSIF {changed} THEN {edit_error}END IF; "
        "IF TG_OP = 'DELETE' THEN RETURN OLD; END IF; RETURN NEW; "
        "END; $ledger$ LANGUAGE plpgsql"
    ).format(
        schema=schema,
        fn=balance_fn,
        flag=flag,
        balance_col=balance_col,
        delete_error=_raise(
            "this balance is maintained by its quantity ledger and cannot be deleted directly"
        ),
        insert_error=_raise("this balance is maintained by its quantity ledger and must start at zero"),
        changed=_any("NEW.{c} IS DISTINCT FROM OLD.{c}", [balance_col, *phys.balance_dims]),
        edit_error=_raise("this balance is maintained by its quantity ledger and cannot be edited directly"),
    )
    balance_trigger_ddl = sql.SQL(
        "CREATE TRIGGER {trigger} BEFORE INSERT OR UPDATE OR DELETE ON {schema}.{balance_tbl} "
        "FOR EACH ROW EXECUTE FUNCTION {schema}.{fn}()"
    ).format(trigger=balance_trigger, schema=schema, balance_tbl=balance_tbl, fn=balance_fn)

    # TRUNCATE fires no row-level trigger, so it would otherwise empty
    # either table without any guard above running.
    truncate_fn_ddl = sql.SQL(
        "CREATE FUNCTION {schema}.{fn}() RETURNS trigger AS $ledger$ "
        "BEGIN {error}RETURN NULL; END; $ledger$ LANGUAGE plpgsql"
    ).format(
        schema=schema,
        fn=truncate_fn,
        error=_raise("this table is maintained by a quantity ledger and cannot be truncated"),
    )
    truncate_trigger_ddls = [
        sql.SQL(
            "CREATE TRIGGER {trigger} BEFORE TRUNCATE ON {schema}.{table} "
            "FOR EACH STATEMENT EXECUTE FUNCTION {schema}.{fn}()"
        ).format(trigger=trigger, schema=schema, table=table, fn=truncate_fn)
        for trigger, table in ((truncate_mv_trigger, movement_tbl), (truncate_bal_trigger, balance_tbl))
    ]

    with connections["tenant"].cursor() as cursor:
        for statement in (
            movement_fn_ddl,
            movement_trigger_ddl,
            movement_guard_fn_ddl,
            movement_guard_trigger_ddl,
            balance_fn_ddl,
            balance_trigger_ddl,
            truncate_fn_ddl,
            *truncate_trigger_ddls,
        ):
            cursor.execute(statement)


def reconcile(binding: QuantityLedgerBinding) -> list[dict]:
    """Every dimension combination whose stored balance differs from the sum
    of its movements -- an empty list means the ledger is consistent.

    The installed triggers make drift impossible for any session that
    cannot alter them; this is the independent check that proves it (and
    the post-restore/post-migration verification that nothing changed
    behind the triggers' back, e.g. by a role that can disable them)."""
    receipt = RuntimeProvision.objects.filter(instance=binding.instance, completed_at__isnull=False).first()
    if receipt is None:
        raise serializers.ValidationError("This instance's runtime is not provisioned.")
    phys = _physical(receipt, binding)
    dims = list(binding.dimensions.all())
    movement_alias = sql.SQL(", ").join(
        sql.SQL("{} AS {}").format(column, sql.Identifier(f"d{i}"))
        for i, column in enumerate(phys.movement_dims)
    )
    movement_group = sql.SQL(", ").join(phys.movement_dims)
    # Plain equality (hash-joinable): both sides' dimensions are never NULL --
    # the movement trigger rejects a NULL, and a balance row can only start at 0.
    join_on = sql.SQL(" AND ").join(
        sql.SQL("b.{bal} = m.{alias}").format(bal=bal, alias=sql.Identifier(f"d{i}"))
        for i, bal in enumerate(phys.balance_dims)
    )
    dim_select = sql.SQL(", ").join(
        sql.SQL("COALESCE(b.{bal}, m.{alias})").format(bal=bal, alias=sql.Identifier(f"d{i}"))
        for i, bal in enumerate(phys.balance_dims)
    )
    statement = sql.SQL(
        "SELECT {dim_select}, COALESCE(b.{balance_col}, 0)::bigint, COALESCE(m.total, 0)::bigint "
        "FROM {schema}.{balance_tbl} b FULL OUTER JOIN ("
        "SELECT {movement_alias}, SUM({movement_col}) AS total "
        "FROM {schema}.{movement_tbl} GROUP BY {movement_group}"
        ") m ON {join_on} "
        "WHERE COALESCE(b.{balance_col}, 0) <> COALESCE(m.total, 0)"
    ).format(
        dim_select=dim_select,
        balance_col=phys.balance_col,
        schema=phys.schema,
        balance_tbl=phys.balance_tbl,
        movement_alias=movement_alias,
        movement_col=phys.movement_col,
        movement_tbl=phys.movement_tbl,
        movement_group=movement_group,
        join_on=join_on,
    )
    with connections["tenant"].cursor() as cursor:
        cursor.execute(statement)
        rows = cursor.fetchall()
    return [
        {
            "dimensions": {
                str(d.balance_relationship_id): str(value)
                for d, value in zip(dims, row[: len(dims)], strict=True)
            },
            "stored": row[len(dims)],
            "expected": row[len(dims) + 1],
        }
        for row in rows
    ]
