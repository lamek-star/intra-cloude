"""Phase 5 -- workflow transition application
(docs/implementation/APP_PLATFORM_PHASE5.md): the concurrency-safe engine
that applies one declared WorkflowTransition to one record. Mirrors
provisioning.py's own reserve-then-execute shape almost exactly -- a
durable receipt row (WorkflowTransitionAttempt) whose `completed_at` is
the single source of truth for "did this already happen," and the same
universal try/except-record-last_error-then-reraise pattern
provisioning.execute() uses for failure bookkeeping. See that module and
exports/recovery.py for the prior art this deliberately does not
reinvent."""

import hashlib
import json

from django.db import transaction
from django.http import Http404
from django.utils import timezone
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError

from audit import services as audit
from audit.models import AuditEvent
from databases import rows as row_ops
from permissions.services import has_permission

from . import records, webhooks
from .models import WorkflowNotificationDelivery, WorkflowTransition, WorkflowTransitionAttempt
from .runtime_plan import physical_name


class TransitionConflict(APIException):
    status_code = 409
    default_detail = (
        "Record state changed, or this Idempotency-Key was already used for a different request."
    )
    default_code = "transition_conflict"


def _fingerprint(transition_id, record_id, idempotency_key) -> str:
    payload = json.dumps(
        {
            "transition": str(transition_id),
            "record": str(record_id),
            "idempotency_key": str(idempotency_key),
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _condition_met(condition, row) -> bool:
    value = row.get(physical_name("f", condition["field_id"]))
    operator = condition["operator"]
    if operator == "eq":
        return value == condition["value"]
    if operator == "ne":
        return value != condition["value"]
    if operator == "is_null":
        return value is None
    return value is not None  # is_not_null


def event(actor, transition, record_id, result=AuditEvent.Result.SUCCESS, **context):
    model = transition.workflow.model
    audit.record(
        actor=actor,
        organization_id=model.instance.organization_id,
        action="app_instance.workflow.transition.apply",
        resource_type="app_model",
        resource_id=model.id,
        result=result,
        context={"transition": str(transition.id), "record_id": str(record_id), **context},
    )


def apply_transition(
    actor, transition: WorkflowTransition, record_id, *, idempotency_key=None
) -> WorkflowTransitionAttempt:
    model = transition.workflow.model
    instance = model.instance
    # Applying a transition IS a record write -- the same database.write
    # capability every ordinary record update already needs, not a second,
    # parallel enforcement path (this project's own capability-based-
    # authorization rule, ADR-0008).
    receipt, table = records.resolve(
        actor, model, "database.write", action="app_instance.workflow.transition.apply"
    )

    if transition.requires_approval and not has_permission(
        actor,
        "app_instance.workflow.approve",
        organization_id=instance.organization_id,
        resource=("app_instance", instance.id),
    ):
        event(actor, transition, record_id, result=AuditEvent.Result.DENIED)
        raise PermissionDenied("app_instance.workflow.approve required")

    fingerprint = _fingerprint(transition.id, record_id, idempotency_key)

    # Reserve: a durable, idempotent attempt row (control-plane DB). This
    # commits on its own before any tenant-side effect runs, exactly like
    # provisioning.reserve()'s own receipt row -- so a crash after this
    # point still leaves a real row a retry can find and resume from.
    with transaction.atomic(durable=True):
        if idempotency_key is not None:
            attempt, created = WorkflowTransitionAttempt.objects.select_for_update().get_or_create(
                record_id=record_id,
                idempotency_key=idempotency_key,
                defaults={
                    "transition": transition,
                    "request_fingerprint": fingerprint,
                    "created_by": actor,
                },
            )
            if not created:
                if attempt.request_fingerprint != fingerprint:
                    raise TransitionConflict("Idempotency-Key already used for a different request.")
                if attempt.completed_at:
                    return attempt  # Replay short-circuit -- no effects re-run.
        else:
            # Opt-in idempotency, matching exports.RestoreJob's own
            # documented behavior: without a key, every call gets a new
            # attempt row, and a blind retry after an actual success can
            # legitimately see a conflict below (from_state no longer
            # matches) -- the caller chose not to make that safe.
            attempt = WorkflowTransitionAttempt.objects.create(
                transition=transition,
                record_id=record_id,
                request_fingerprint=fingerprint,
                created_by=actor,
            )

    # Execute: evaluate conditions against the record's current values,
    # then one compare-and-swap UPDATE for the state change and any
    # declared field actions together.
    try:
        state_column = physical_name("f", str(transition.workflow.state_field_id))
        try:
            row = row_ops.get_row(table, record_id)
        except row_ops.RowNotFound as exc:
            raise Http404("Record not found.") from exc

        for condition in transition.conditions:
            if not _condition_met(condition, row):
                raise ValidationError("A required condition for this transition is not met.")

        expected = {}
        if transition.from_state_id is not None:
            expected[state_column] = transition.from_state.key
        write = {state_column: transition.to_state.key}
        for action in transition.field_actions:
            write[physical_name("f", action["field_id"])] = action["value"]

        try:
            with transaction.atomic(using="tenant", durable=True):
                row_ops.update_row_if(table, record_id, expected=expected, data=write)
        except row_ops.RowNotFound as exc:
            raise Http404("Record not found.") from exc
        except row_ops.RowConflict as exc:
            raise TransitionConflict("Record state changed; transition no longer applies.") from exc

        delivery = None
        with transaction.atomic(durable=True):
            attempt.state_before = row.get(state_column) or ""
            attempt.state_after = transition.to_state.key
            attempt.completed_at = timezone.now()
            attempt.save(update_fields=["state_before", "state_after", "completed_at"])
            event(actor, transition, record_id, to_state=transition.to_state.key)
            if transition.notify_url:
                delivery = WorkflowNotificationDelivery.objects.create(
                    attempt=attempt, url=transition.notify_url
                )
        if delivery is not None:
            # Only enqueued once the completion above is durably
            # committed (transaction.on_commit) -- a crash before that
            # point means this attempt never sent a notification, and a
            # later retry that completes it queues one for real then,
            # never twice (recovery.py's own post-publish side-effect
            # discipline).
            delivery_id = delivery.id
            transaction.on_commit(lambda: _enqueue_delivery(delivery_id))
        # Phase 10: a second, independent dispatch to any EnvironmentWebhook
        # subscribed on the Environment this instance's runtime database is
        # bound to -- never coupled to notify_url (a transition with no
        # notify_url at all still fires this if a webhook is subscribed,
        # and vice versa).
        payload = {
            "transition": {"key": transition.key, "label": transition.label},
            "from_state": transition.from_state.key if transition.from_state_id else None,
            "to_state": transition.to_state.key,
            "record_id": str(record_id),
        }
        transaction.on_commit(
            lambda: webhooks.dispatch_event(receipt, instance, webhooks.EVENT_WORKFLOW_TRANSITION, payload)
        )
        return attempt
    except Exception as exc:
        with transaction.atomic():
            # Same lock-then-check-completed_at discipline as
            # provisioning.execute()'s own except block -- never overwrite
            # a receipt that a concurrent call already finished
            # successfully.
            locked = WorkflowTransitionAttempt.objects.select_for_update().filter(pk=attempt.pk).first()
            if locked and not locked.completed_at:
                locked.last_error = f"{type(exc).__name__}: {exc}"[:200]
                locked.save(update_fields=["last_error"])
        raise


def _enqueue_delivery(delivery_id):
    # Deferred import: keeps this module free of a Celery import at
    # process start for any test/context that never applies a
    # notification-bearing transition.
    from .tasks import deliver_workflow_notification

    deliver_workflow_notification.delay(str(delivery_id))
