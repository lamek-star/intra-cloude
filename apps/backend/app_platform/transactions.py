"""Atomic multi-record business operations (ADR-0016; Local Edition P0: no
partial business transaction commit).

A real sale is several records -- an order, its lines, the stock movements
that take goods out, an invoice -- and any one of them can fail (stock ran
out, a permission was revoked, a value was invalid). Committed one request
at a time, a failure midway would leave an order with no stock deducted, or
stock deducted with no order. This module runs an ordered list of create/
update operations inside ONE tenant transaction, so all of it commits or
none of it does.

It composes the existing record services rather than replacing them: every
operation goes through `records.create_record` / `records.update_record`, so
per-model `database.write` checks, organizational-unit scope, validation,
the quantity-ledger triggers and the durable operation journal all apply to
each step exactly as they do for a single-record request. The journal's
audit/webhook projection is scheduled with `transaction.on_commit`, so it
fires only if the whole transaction commits. Inventory arithmetic is never
done here -- a movement operation just inserts a Stock Movement and the
ledger triggers (quantity_ledger.py) decide the resulting balance.

An operation may name its created record with `ref` and later operations may
refer to its id with `{"$ref": "<name>"}` (in a field value, a list of ids,
or an update's `record`). References resolve to earlier operations only.
Every model must belong to the one instance in the URL, so a model id from
another instance or organization is simply "unknown".
"""

from django.db import transaction
from rest_framework import serializers

from databases import rows as row_ops

from . import instances, records
from .definitions import StrictSerializer
from .models import AppInstance

MAX_OPERATIONS = 100
_REF_KEY = "$ref"


class OperationInput(StrictSerializer):
    op = serializers.ChoiceField(choices=["create", "update"])
    model = serializers.UUIDField()
    # The record an `update` targets: a record id, or {"$ref": "<name>"}.
    record = serializers.JSONField(required=False)
    data = serializers.DictField()  # type: ignore[assignment]  # DRF declarative field, removed by its metaclass
    ref = serializers.RegexField(r"^[a-z][a-z0-9_]{0,31}$", required=False)


class TransactionInput(StrictSerializer):
    operations = serializers.ListField(child=OperationInput(), min_length=1, max_length=MAX_OPERATIONS)  # type: ignore[assignment]


class TransactionError(Exception):
    """One operation was invalid or rejected; the whole transaction rolled back."""

    def __init__(self, index: int, message: str):
        super().__init__(message)
        self.index = index


class TransactionDenied(TransactionError):
    """The actor lacks authority for one operation; the whole transaction rolled back."""


def _resolve(value, created: dict, index: int):
    if isinstance(value, dict) and set(value) == {_REF_KEY}:
        name = value[_REF_KEY]
        if not isinstance(name, str) or name not in created:
            raise TransactionError(
                index, f"unknown reference: {name!r} (references resolve to earlier operations)"
            )
        return created[name]["id"]
    if isinstance(value, list):
        return [_resolve(item, created, index) for item in value]
    return value


def run(
    actor,
    instance: AppInstance,
    data,
    *,
    idempotency_key: str | None = None,
    movement_operation: str | None = None,
) -> list[dict]:
    """Runs every operation in order inside one tenant transaction and
    returns each operation's resulting record. `idempotency_key` covers the
    whole transaction: each create derives its own stable per-operation key
    from it, so replaying the same request returns the same records without
    inserting (or re-firing the ledger) again.

    `movement_operation` is passed ONLY by the server-side business operations (inventory_operations.py) and
    names the operation that authorizes the stock movements they build; the HTTP transaction endpoint never
    sets it, so a movement in an ordinary transaction needs `inventory.adjust` (ADR-0017)."""
    values = instances.validated(TransactionInput, data)
    models: dict = {}
    created: dict = {}
    results: list[dict] = []
    with transaction.atomic(using="tenant"):
        for index, operation in enumerate(values["operations"]):
            model_id = operation["model"]
            model = models.get(model_id)
            if model is None:
                model = instance.models.filter(pk=model_id).first()
                if model is None:
                    raise TransactionError(index, "unknown model for this instance")
                models[model_id] = model
            ref = operation.get("ref")
            if ref is not None and ref in created:
                raise TransactionError(index, f"duplicate reference: {ref!r}")
            payload = {key: _resolve(value, created, index) for key, value in operation["data"].items()}
            try:
                if operation["op"] == "create":
                    key = f"{idempotency_key}:{index}" if idempotency_key else None
                    row = records.create_record(
                        actor, model, payload, idempotency_key=key, movement_operation=movement_operation
                    )
                else:
                    if "record" not in operation:
                        raise TransactionError(index, "an update needs a record")
                    record_id = _resolve(operation["record"], created, index)
                    row = records.update_record(actor, model, record_id, payload)
            except records.RecordAccessDenied as exc:
                raise TransactionDenied(index, str(exc)) from exc
            except (records.RecordValueError, row_ops.RowNotFound) as exc:
                raise TransactionError(index, str(exc) or "record not found") from exc
            if ref is not None:
                created[ref] = row
            results.append({"operation": index, "model": str(model.id), "ref": ref, "record": row})
    return results
