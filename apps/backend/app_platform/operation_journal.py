"""Tenant-atomic record events with replayable control-plane publication (ADR-0016).

Only ids and audit metadata cross into the control plane. An unpublished
entry survives the API process, worker, broker, or control database failing.
"""

import hashlib
import json
import logging
import uuid
from functools import partial

from django.db import connections, transaction
from psycopg import sql
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.utils.encoders import JSONEncoder

from accounts.models import User
from audit.models import AuditEvent

from .models import RecordAttachment, RuntimeProvision

logger = logging.getLogger(__name__)
TABLE = "__intraforge_operations"


class IdempotencyConflict(APIException):
    status_code = 409
    default_detail = "Idempotency-Key was already used for a different request."


def request_identity(actor, model, key: str | None, data: dict):
    if key is None:
        return None, None
    if not isinstance(key, str) or not key.strip() or len(key) > 128:
        raise ValidationError("Idempotency-Key must contain 1 to 128 characters.")
    identity = hashlib.sha256(f"{actor.pk}:{model.pk}:{key}".encode()).hexdigest()
    fingerprint = hashlib.sha256(json.dumps(data, sort_keys=True, cls=JSONEncoder).encode()).hexdigest()
    return identity, fingerprint


def replay(receipt, identity, fingerprint):
    if identity is None:
        return None
    with connections["tenant"].cursor() as cursor:
        # Same actor/model/key serializes concurrent creates, even before a row exists.
        lock = int.from_bytes(bytes.fromhex(identity)[:8], "big", signed=True)
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [lock])
        cursor.execute(
            sql.SQL("SELECT event FROM {} WHERE event->>'request_key' = %s").format(
                sql.Identifier(receipt.database.schema_name, TABLE)
            ),
            [identity],
        )
        row = cursor.fetchone()
    if row is None:
        return None
    event = json.loads(row[0]) if isinstance(row[0], str) else row[0]
    if event["request_fingerprint"] != fingerprint:
        raise IdempotencyConflict()
    return event["response"]


def install(schema_name: str) -> None:
    """Internal DDL: invoked only by provisioning or the operator upgrade command."""
    if not connections["tenant"].in_atomic_block:
        raise RuntimeError("Journal installation requires a tenant transaction")
    with connections["tenant"].cursor() as cursor:
        cursor.execute(
            sql.SQL("""
            CREATE TABLE IF NOT EXISTS {} (
                id uuid PRIMARY KEY,
                event jsonb NOT NULL,
                created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
                published_at timestamptz
            )
        """).format(sql.Identifier(schema_name, TABLE))
        )
        cursor.execute(
            sql.SQL("CREATE UNIQUE INDEX IF NOT EXISTS {} ON {} ((event->>'request_key'))").format(
                sql.Identifier("__intraforge_operations_request"), sql.Identifier(schema_name, TABLE)
            )
        )
        cursor.execute(
            sql.SQL("CREATE INDEX IF NOT EXISTS {} ON {} (created_at, id) WHERE published_at IS NULL").format(
                sql.Identifier("__intraforge_operations_pending"), sql.Identifier(schema_name, TABLE)
            )
        )


def append(
    receipt,
    actor,
    model,
    action: str,
    record_id,
    *,
    request_key=None,
    request_fingerprint=None,
    response=None,
    **context,
) -> uuid.UUID:
    if not connections["tenant"].in_atomic_block:
        raise RuntimeError("Journal append must share the record's transaction")
    from .webhooks import subscribers

    event_id = uuid.uuid4()
    event = {
        "actor_id": str(actor.pk),
        "organization_id": str(model.instance.organization_id),
        "action": f"app_instance.{action}",
        "model_id": str(model.pk),
        "context": {"record_id": str(record_id), **context},
        "payload": {"model": {"id": str(model.pk), "key": model.key}, "record_id": str(record_id)},
        "webhooks": [str(webhook.pk) for webhook in subscribers(receipt, f"app_instance.{action}")],
    }
    if request_key is not None:
        event.update(request_key=request_key, request_fingerprint=request_fingerprint, response=response)
    with connections["tenant"].cursor() as cursor:
        cursor.execute(
            sql.SQL("INSERT INTO {} (id, event) VALUES (%s, %s::jsonb)").format(
                sql.Identifier(receipt.database.schema_name, TABLE)
            ),
            [event_id, json.dumps(event, cls=JSONEncoder)],
        )
    # Both databases must be out of the caller's transactions before projection.
    transaction.on_commit(partial(_after_tenant_commit, receipt.pk, event_id), using="tenant")
    return event_id


def _after_tenant_commit(receipt_id, event_id):
    transaction.on_commit(partial(publish_safely, receipt_id, event_id))


def publish_safely(receipt_id, event_id=None) -> None:
    try:
        publish(receipt_id, event_id)
    except Exception:  # noqa: BLE001 - committed operation remains durably pending for the scheduled recovery
        logger.exception("Operation journal publication deferred for runtime %s", receipt_id)


def publish(receipt_id, event_id=None, *, limit: int = 100) -> int:
    """Replay a bounded batch. Stable identities deduplicate a crash after control commit."""
    from .webhooks import publish_delivery

    receipt = RuntimeProvision.objects.select_related("database", "instance").get(pk=receipt_id)
    if receipt.database is None:
        return 0
    identifier = sql.Identifier(receipt.database.schema_name, TABLE)
    with transaction.atomic(using="tenant"), connections["tenant"].cursor() as cursor:
        clause = sql.SQL("AND id = %s") if event_id else sql.SQL("")
        parameters = [event_id, limit] if event_id else [limit]
        cursor.execute(
            sql.SQL(
                "SELECT id, event FROM {} WHERE published_at IS NULL {} "
                "ORDER BY created_at, id LIMIT %s FOR UPDATE SKIP LOCKED"
            ).format(identifier, clause),
            parameters,
        )
        entries = cursor.fetchall()
        for identity, event in entries:
            if isinstance(event, str):
                event = json.loads(event)
            with transaction.atomic(durable=True):
                actor_id = event["actor_id"] if User.objects.filter(pk=event["actor_id"]).exists() else None
                AuditEvent.objects.get_or_create(
                    pk=identity,
                    defaults={
                        "actor_id": actor_id,
                        "organization_id": receipt.instance.organization_id,
                        "action": event["action"],
                        "resource_type": "app_model",
                        "resource_id": event["model_id"],
                        "result": AuditEvent.Result.SUCCESS,
                        "context": event["context"],
                    },
                )
                if event["action"] == "app_instance.record.delete":
                    RecordAttachment.objects.filter(
                        model_id=event["model_id"], record_id=event["context"]["record_id"]
                    ).delete()
                for webhook_id in event["webhooks"]:
                    publish_delivery(
                        receipt,
                        event["action"],
                        event["payload"],
                        webhook_id,
                        identity=uuid.uuid5(identity, webhook_id),
                    )
            cursor.execute(
                sql.SQL("UPDATE {} SET published_at = CURRENT_TIMESTAMP WHERE id = %s").format(identifier),
                [identity],
            )
        return len(entries)
