"""After the scale run: the ledger still holds at 5,000 products / 10,000 movements (via `manage.py shell`).

Reads the database directly (never through the browser) and prints one JSON line:
  * `drift`      rows whose stored balance differs from the sum of their movements  (must be [])
  * `balances`   number of balance rows and their total on hand
  * `movements`  number of movements and the sum of their deltas (must equal the total on hand)
"""

import json

from django.db import connections
from psycopg import sql

from app_platform import quantity_ledger, schema_evolution
from app_platform.models import AppInstance, QuantityLedgerBinding, RuntimeProvision
from organizations.models import Organization

org = Organization.objects.get(name="Scale Qualification Shop")
instance = AppInstance.objects.get(organization=org)
receipt = RuntimeProvision.objects.get(instance=instance)
models = {m.key: m for m in instance.models.all()}
binding = QuantityLedgerBinding.objects.get(instance=instance)


def table(key):
    physical = schema_evolution._table_for(receipt, models[key])
    return sql.SQL("{}.{}").format(sql.Identifier(physical.tenant_database.schema_name), sql.Identifier(physical.name))


def column(model_key, field_key):
    return sql.Identifier(schema_evolution._column_for(receipt, models[model_key].fields.get(key=field_key)).name)


with connections["tenant"].cursor() as cursor:
    cursor.execute(sql.SQL("SELECT count(*), coalesce(sum({}), 0) FROM {}").format(column("inventory", "quantity_on_hand"), table("inventory")))
    balance_rows, on_hand = cursor.fetchone()
    cursor.execute(sql.SQL("SELECT count(*), coalesce(sum({}), 0) FROM {}").format(column("stock_movement", "quantity_delta"), table("stock_movement")))
    movement_rows, delta_sum = cursor.fetchone()
print(json.dumps({
    "drift": quantity_ledger.reconcile(binding),
    "balances": {"rows": balance_rows, "on_hand": int(on_hand)},
    "movements": {"rows": movement_rows, "sum_of_deltas": int(delta_sum)},
    "equal": int(on_hand) == int(delta_sum),
}))
