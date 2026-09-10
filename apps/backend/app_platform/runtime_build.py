"""Validated tenant/catalog construction inside provisioning's transactions."""

import uuid

from django.db import connections
from psycopg import sql

from databases import services
from databases.models import TenantDatabase


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
            )
            bindings["fields"][field["definition_id"]] = str(column.id)
    for relation in plan["relationships"]:
        source, target = tables[relation["source_model"]], tables[relation["target_model"]]
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
