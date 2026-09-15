"""Validated tenant/catalog construction inside provisioning's transactions."""

import uuid

from django.db import connections
from psycopg import sql

from databases import services
from databases.models import DBForeignKey, TenantDatabase


class RuntimeReconciliationRequired(Exception):
    pass


def marker(receipt):
    return f"intraforge-runtime-v1:{receipt.instance_id}:{receipt.fingerprint}"


def reconcile(receipt):
    plan = receipt.plan
    with connections["tenant"].cursor() as cursor:
        lock_id = int.from_bytes(receipt.instance_id.bytes[:8], "big", signed=True)
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [lock_id])
        if (
            TenantDatabase.objects.filter(id=plan["database_id"]).exists()
            or TenantDatabase.objects.filter(schema_name=plan["schema_name"]).exists()
        ):
            raise RuntimeReconciliationRequired("Pending runtime schema already has a catalog owner")
        cursor.execute(
            "SELECT obj_description(oid, 'pg_namespace') FROM pg_namespace WHERE nspname = %s",
            [plan["schema_name"]],
        )
        row = cursor.fetchone()
        if row:
            if row[0] != marker(receipt):
                raise RuntimeReconciliationRequired("Runtime schema lacks its operation ownership marker")
            cursor.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(plan["schema_name"])))


def _build_join_table(actor, database, relation, source_table, target_table):
    """A many_to_many relationship's pivot table -- two fixed-name FK
    columns (never per-identity UUID-hex names, unlike every other
    physical column in this app: a join table is purpose-built and never
    user-editable, so there's no naming collision to guard against, and
    literal names are far more debuggable), both ON DELETE CASCADE so a
    base-row delete on either side removes the association for free
    (see records.py's delete_record). The composite unique constraint's
    own index already serves source_id lookups as its leading column, so
    only target_id gets a second, explicit index."""
    join_table = services.create_table(actor=actor, tenant_database=database, name=relation["join_table"])
    source_column = services.add_column(
        actor=actor, table=join_table, name=relation["source_column"], data_type="uuid", is_nullable=False
    )
    target_column = services.add_column(
        actor=actor, table=join_table, name=relation["target_column"], data_type="uuid", is_nullable=False
    )
    source_fk = services.add_foreign_key(
        actor=actor,
        column=source_column,
        references_table=source_table,
        references_column=source_table.columns.get(is_primary_key=True),
        on_delete=DBForeignKey.OnDelete.CASCADE,
    )
    target_fk = services.add_foreign_key(
        actor=actor,
        column=target_column,
        references_table=target_table,
        references_column=target_table.columns.get(is_primary_key=True),
        on_delete=DBForeignKey.OnDelete.CASCADE,
    )
    unique_index = services.add_composite_unique_constraint(
        actor=actor, table=join_table, column_a=source_column, column_b=target_column
    )
    target_index = services.add_index(actor=actor, column=target_column)
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


def build(receipt, actor):
    plan = receipt.plan
    database = services.create_tenant_database(
        actor=actor,
        project=receipt.instance.project,
        name=f"App runtime {receipt.instance_id}",
        _database_id=uuid.UUID(plan["database_id"]),
    )
    tables = {}
    bindings = {"models": {}, "fields": {}, "relationships": {}}
    for model in plan["models"]:
        table = services.create_table(actor=actor, tenant_database=database, name=model["name"])
        tables[model["definition_id"]] = table
        bindings["models"][model["definition_id"]] = str(table.id)
        field_columns = {}
        for field in model["columns"]:
            column = services.add_column(
                actor=actor,
                table=table,
                name=field["name"],
                data_type=field["data_type"],
                is_nullable=field["is_nullable"],
                precision=field["precision"],
                scale=field["scale"],
                default_value=field["default"],
                is_unique=field.get("unique", False),
                is_indexed=field.get("indexed", False),
            )
            bindings["fields"][field["definition_id"]] = str(column.id)
            field_columns[field["definition_id"]] = column
        for constraint in model.get("constraints", []):
            index = services.add_field_set_unique_constraint(
                actor=actor,
                table=table,
                columns=[field_columns[field_id] for field_id in constraint["field_ids"]],
                constraint_id=uuid.UUID(constraint["definition_id"]),
            )
            bindings.setdefault("constraints", {})[constraint["definition_id"]] = str(index.id)
    for relation in plan["relationships"]:
        source, target = tables[relation["source_model"]], tables[relation["target_model"]]
        if relation["kind"] == "many_to_many":
            bindings["relationships"][relation["definition_id"]] = _build_join_table(
                actor, database, relation, source, target
            )
            continue
        column = services.add_column(
            actor=actor,
            table=source,
            name=relation["column"],
            data_type="uuid",
            is_nullable=True,
        )
        foreign_key = services.add_foreign_key(
            actor=actor,
            column=column,
            references_table=target,
            references_column=target.columns.get(is_primary_key=True),
            on_delete=relation["on_delete"],
        )
        bindings["relationships"][relation["definition_id"]] = {
            "kind": "many_to_one",
            "column": str(column.id),
            "foreign_key": str(foreign_key.id),
        }
    with connections["tenant"].cursor() as cursor:
        cursor.execute(
            sql.SQL("COMMENT ON SCHEMA {} IS {}").format(
                sql.Identifier(database.schema_name),
                sql.Literal(marker(receipt)),
            )
        )
    return database, bindings
