"""Independent, read-only check of what the flagship browser journey left in PostgreSQL.

Run via `manage.py shell` in the qualification runner/backend (production settings). It looks at the
most recent Spare Parts instances (`FLAGSHIP_INSTANCES`, default 1) and asserts, straight from the
tenant schema and the control database -- never through the UI or the API -- that:

  * the on-hand balance is 95, held by the DATABASE ledger, and the ledger reconciles to its movements;
  * there are exactly two movements: +100 (receive) and -5 (sale, referencing the invoice number);
  * exactly one sales order, one line and one invoice exist (nothing from the refused oversell);
  * the receive with a supplier recorded one received purchase order and line;
  * the ledger triggers are installed, and the attached document is stored.

A green browser run that did not leave exactly this state is a false positive.
"""

import os
import sys

from django.db import connections
from psycopg import sql

from app_platform import quantity_ledger, schema_evolution
from app_platform.models import AppInstance, QuantityLedgerBinding, RecordAttachment, RuntimeProvision

WANTED = int(os.environ.get("FLAGSHIP_INSTANCES", "1"))
failures = []


def check(name, ok, detail=""):
    print(("PASS  " if ok else "FAIL  ") + name + (f"  -- {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


def rows(query, params=None):
    with connections["tenant"].cursor() as cursor:
        cursor.execute(query, params)
        return cursor.fetchall()


for instance in AppInstance.objects.filter(label="Spare Parts").order_by("-created_at")[:WANTED]:
    print(f"\n=== instance {instance.id} (created {instance.created_at:%Y-%m-%d %H:%M:%S})")
    receipt = RuntimeProvision.objects.get(instance=instance)
    models = {m.key: m for m in instance.models.all()}

    def table(key):
        physical = schema_evolution._table_for(receipt, models[key])
        return sql.SQL("{}.{}").format(sql.Identifier(physical.tenant_database.schema_name), sql.Identifier(physical.name))

    def column(model_key, field_key):
        return sql.Identifier(schema_evolution._column_for(receipt, models[model_key].fields.get(key=field_key)).name)

    def count(key):
        return rows(sql.SQL("SELECT count(*) FROM {}").format(table(key)))[0][0]

    balance = column("inventory", "quantity_on_hand")
    check("exactly one stock balance row", count("inventory") == 1, str(count("inventory")))
    on_hand = [r[0] for r in rows(sql.SQL("SELECT {} FROM {}").format(balance, table("inventory")))]
    check("the ledger holds an on-hand balance of 95", on_hand == [95], str(on_hand))

    delta, kind, reference, when = (
        column("stock_movement", "quantity_delta"),
        column("stock_movement", "movement_type"),
        column("stock_movement", "reference"),
        column("stock_movement", "occurred_at"),
    )
    movements = rows(sql.SQL("SELECT {}, {}, {} FROM {} ORDER BY {}").format(delta, kind, reference, table("stock_movement"), when))
    check("exactly two movements: +100 receive, -5 sale", [(m[0], m[1]) for m in movements] == [(100, "receive"), (-5, "sale")], str(movements))

    check("exactly one sales order", count("sales_order") == 1, str(count("sales_order")))
    check("exactly one sales order line", count("sales_order_line") == 1, str(count("sales_order_line")))
    check("exactly one invoice", count("invoice") == 1, str(count("invoice")))
    invoice = rows(
        sql.SQL("SELECT {}, {} FROM {}").format(column("invoice", "invoice_number"), column("invoice", "amount_due"), table("invoice"))
    )
    check(
        "the invoice number is the sale movement's reference and it is due 75.00",
        len(invoice) == 1 and len(movements) == 2 and invoice[0][0] == movements[1][2] and float(invoice[0][1]) == 75.0,
        f"{invoice} vs {movements}",
    )
    check("the supplier receive recorded one purchase order and one line", count("purchase_order") == 1 and count("purchase_order_line") == 1)

    binding = QuantityLedgerBinding.objects.filter(instance=instance).first()
    check("a quantity ledger is bound", binding is not None)
    if binding is not None:
        drift = quantity_ledger.reconcile(binding)
        check("stored balances equal the sum of their movements (reconcile)", drift == [], str(drift))
    schema_name = schema_evolution._table_for(receipt, models["inventory"]).tenant_database.schema_name
    triggers = rows(
        "SELECT count(*) FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = %s AND NOT t.tgisinternal AND t.tgname LIKE 'trg_ledger_%%'",
        [schema_name],
    )[0][0]
    check("the ledger triggers are installed in the tenant schema", triggers >= 4, str(triggers))
    check("one attached document is stored", RecordAttachment.objects.filter(model=models["part"]).count() == 1)

print()
if failures:
    print(f"{len(failures)} check(s) FAILED:", *failures, sep="\n  ")
    sys.exit(1)
print("all checks passed")
