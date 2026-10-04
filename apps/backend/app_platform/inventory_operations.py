"""Controlled business operations over an installed inventory application: SELL and RECEIVE (ADR-0017).

The browser states an INTENT -- "sell these lines to this customer", "receive this quantity of this
part into this warehouse" -- and the server builds the records and commits them as one atomic
transaction. Three concerns stay separate:

* AUTHORITY: `inventory.sell` / `inventory.receive` (inventory_authority.py) answer "may this actor
  perform this operation?". Holding one implies none of the others.
* ATOMICITY: `transactions.run` commits the order, its lines, the stock movements and the invoice (or
  the purchase order, its line and the movement) together or not at all.
* INTEGRITY: the movements are ordinary inserts; the PostgreSQL quantity ledger alone decides whether
  the resulting balance is valid. Nothing here does inventory arithmetic, and an oversell is refused
  by the database.

Existing authorization still applies to everything the operation writes besides the stock movement:
the actor needs write access to the sales-order, order-line and invoice models for a sale (and, when a
supplier is recorded, to the purchase-order models for a receive), enforced by the same
`records.create_record` checks as any other write. The movement itself is authorized by the operation,
not by raw write access to the stock tables -- so a cashier holds `inventory.sell`, not write access
to inventory.

An ordinary user therefore cannot create arbitrary stock movements: the record API and the generic
transaction endpoint require `inventory.adjust` for any movement (records.py), and only this module
passes a named operation.
"""

import datetime

from django.utils import timezone
from rest_framework import serializers

from audit import services as audit

from . import instances, inventory_authority, transactions
from .definitions import StrictSerializer
from .models import AppInstance, ModelDefinition, QuantityLedgerBinding

MAX_SALE_LINES = 50
_PLATFORM_TIMESTAMP = "%Y-%m-%dT%H:%M:%S"  # naive UTC, whole seconds (databases/formats.py)
_MAX_AGE = datetime.timedelta(days=31)
_MAX_SKEW = datetime.timedelta(hours=1)


class OperationUnsupported(Exception):
    """The installed application does not carry the models this operation needs."""


class SaleLineInput(StrictSerializer):
    part = serializers.UUIDField()
    warehouse = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=1_000_000)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)


def _timestamp(value: str) -> datetime.datetime:
    try:
        moment = datetime.datetime.strptime(value, _PLATFORM_TIMESTAMP)
    except (TypeError, ValueError) as exc:
        raise serializers.ValidationError(
            f"Use the platform timestamp form {_PLATFORM_TIMESTAMP} (UTC)."
        ) from exc
    now = timezone.now().replace(tzinfo=None)
    if moment < now - _MAX_AGE or moment > now + _MAX_SKEW:
        raise serializers.ValidationError(
            "occurred_at must be within the last 31 days and not in the future."
        )
    return moment


class SellInput(StrictSerializer):
    customer = serializers.UUIDField()
    invoice_number = serializers.RegexField(r"^[A-Za-z0-9][A-Za-z0-9-]{0,39}$")
    occurred_at = serializers.CharField()
    lines = serializers.ListField(child=SaleLineInput(), min_length=1, max_length=MAX_SALE_LINES)  # type: ignore[assignment]

    def validate_occurred_at(self, value):
        return _timestamp(value)


class ReceiveInput(StrictSerializer):
    part = serializers.UUIDField()
    warehouse = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=1_000_000)
    supplier = serializers.UUIDField(required=False, allow_null=True, default=None)
    unit_cost = serializers.DecimalField(
        required=False, allow_null=True, default=None, max_digits=12, decimal_places=2, min_value=0
    )
    reference = serializers.CharField(required=False, allow_blank=True, max_length=200, default="")
    occurred_at = serializers.CharField()

    def validate_occurred_at(self, value):
        return _timestamp(value)


def _money(value) -> str:
    return f"{value:.2f}"


class _Builder:
    """Builds operations in the transaction endpoint's own format, addressed by the template's
    model/field keys
    (never by hard-coded ids), and refuses an application that does not carry the models it needs."""

    def __init__(self, instance: AppInstance, model_keys: list[str]):
        self.models: dict[str, ModelDefinition] = {m.key: m for m in instance.models.all()}
        missing = [key for key in model_keys if key not in self.models]
        if missing:
            raise OperationUnsupported(f"This application has no {', '.join(missing)} model.")
        movement = self.models["stock_movement"]
        if not QuantityLedgerBinding.objects.filter(instance=instance, movement_model=movement).exists():
            raise OperationUnsupported("This application does not keep a stock ledger.")
        self._ids: dict[tuple[str, str], str] = {}

    def _id(self, model_key: str, key: str) -> str:
        if (model_key, key) not in self._ids:
            model = self.models[model_key]
            found = model.fields.filter(key=key).first()
            self._ids[(model_key, key)] = str(
                found.id if found is not None else model.outgoing.get(key=key).id
            )
        return self._ids[(model_key, key)]

    def create(self, model_key: str, ref: str | None = None, **values) -> dict:
        item = {
            "op": "create",
            "model": str(self.models[model_key].id),
            "data": {self._id(model_key, key): value for key, value in values.items() if value is not None},
        }
        if ref:
            item["ref"] = ref
        return item


def _commit(actor, instance, operations, idempotency_key, operation: str) -> list[dict]:
    if not idempotency_key:
        raise serializers.ValidationError(
            {"Idempotency-Key": "This header is required for a business operation."}
        )
    return transactions.run(
        actor,
        instance,
        {"operations": operations},
        idempotency_key=idempotency_key,
        movement_operation=operation,
    )


def sell(actor, instance: AppInstance, data, *, idempotency_key: str | None) -> list[dict]:
    """Sales order + one line and one stock-out movement per item + invoice, atomically."""
    inventory_authority.require(actor, instance, inventory_authority.SELL, action="inventory.sell")
    values = instances.validated(SellInput, data)
    build = _Builder(instance, ["sales_order", "sales_order_line", "invoice", "stock_movement"])
    day = values["occurred_at"].date().isoformat()
    stamp = values["occurred_at"].strftime(_PLATFORM_TIMESTAMP)
    total = sum(line["unit_price"] * line["quantity"] for line in values["lines"])
    operations = [
        build.create(
            "sales_order",
            "order",
            customer=str(values["customer"]),
            status="confirmed",
            order_date=day,
            total_amount=_money(total),
        )
    ]
    for line in values["lines"]:
        operations.append(
            build.create(
                "sales_order_line",
                sales_order_line_sales_order={"$ref": "order"},
                sales_order_line_part=str(line["part"]),
                quantity=line["quantity"],
                unit_price=_money(line["unit_price"]),
                line_total=_money(line["unit_price"] * line["quantity"]),
            )
        )
        operations.append(
            build.create(
                "stock_movement",
                stock_movement_part=str(line["part"]),
                stock_movement_warehouse=str(line["warehouse"]),
                quantity_delta=-line["quantity"],
                movement_type="sale",
                reference=values["invoice_number"],
                occurred_at=stamp,
            )
        )
    operations.append(
        build.create(
            "invoice",
            invoice_number=values["invoice_number"],
            invoice_sales_order={"$ref": "order"},
            invoice_date=day,
            amount_due=_money(total),
            status="unpaid",
        )
    )
    results = _commit(actor, instance, operations, idempotency_key, inventory_authority.SELL)
    order = next(r for r in results if r["ref"] == "order")
    audit.record(
        actor=actor,
        organization_id=instance.organization_id,
        action="inventory.sell",
        resource_type="app_instance",
        resource_id=instance.id,
        context={
            "order_id": str(order["record"]["id"]),
            "invoice_number": values["invoice_number"],
            "lines": len(values["lines"]),
            "total": _money(total),
        },
    )
    return results


def receive(actor, instance: AppInstance, data, *, idempotency_key: str | None) -> list[dict]:
    """One stock-in movement, plus -- when a supplier is recorded -- a received purchase order and
    its line."""
    inventory_authority.require(actor, instance, inventory_authority.RECEIVE, action="inventory.receive")
    values = instances.validated(ReceiveInput, data)
    supplier = values["supplier"]
    keys = ["stock_movement"] + (["purchase_order", "purchase_order_line"] if supplier else [])
    build = _Builder(instance, keys)
    day = values["occurred_at"].date().isoformat()
    stamp = values["occurred_at"].strftime(_PLATFORM_TIMESTAMP)
    operations = []
    if supplier:
        unit = values["unit_cost"] or 0
        total = unit * values["quantity"]
        operations.append(
            build.create(
                "purchase_order",
                "po",
                supplier=str(supplier),
                status="received",
                order_date=day,
                total_amount=_money(total),
            )
        )
        operations.append(
            build.create(
                "purchase_order_line",
                purchase_order={"$ref": "po"},
                purchase_order_line_part=str(values["part"]),
                quantity=values["quantity"],
                unit_cost=_money(unit),
                line_total=_money(total),
            )
        )
    operations.append(
        build.create(
            "stock_movement",
            stock_movement_part=str(values["part"]),
            stock_movement_warehouse=str(values["warehouse"]),
            quantity_delta=values["quantity"],
            movement_type="receive",
            reference=(values["reference"] or "").strip() or None,
            occurred_at=stamp,
        )
    )
    results = _commit(actor, instance, operations, idempotency_key, inventory_authority.RECEIVE)
    audit.record(
        actor=actor,
        organization_id=instance.organization_id,
        action="inventory.receive",
        resource_type="app_instance",
        resource_id=instance.id,
        context={
            "part_id": str(values["part"]),
            "warehouse_id": str(values["warehouse"]),
            "quantity": values["quantity"],
        },
    )
    return results
