"""Durable reservation, replay and publication of a generated app database."""

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from audit import services as audit
from audit.models import AuditEvent

from . import runtime_build
from .access import check, require_manage
from .models import AppInstance, RuntimeProvision
from .runtime_plan import plan_runtime


class RuntimeConflict(APIException):
    status_code = 409
    default_detail = "Runtime plan changed; refresh the preview before provisioning."
    default_code = "runtime_conflict"


def require_provision(actor, instance):
    require_manage(actor, instance)
    for capability in ("database.create", "database.schema.manage"):
        check(actor, instance.organization_id, capability)


def reserve(actor, instance, fingerprint):
    require_provision(actor, instance)
    # This receipt MUST survive before any tenant DDL. Refuse a surrounding
    # production transaction rather than accidentally publish it too late.
    with transaction.atomic(durable=True):
        instance = AppInstance.objects.select_for_update().get(pk=instance.pk)
        plan = plan_runtime(actor, instance)
        if fingerprint != plan["fingerprint"]:
            raise RuntimeConflict()
        receipt = RuntimeProvision.objects.filter(instance=instance).first()
        if receipt:
            if receipt.fingerprint != fingerprint:
                raise RuntimeConflict()
            return receipt
        receipt = RuntimeProvision.objects.create(
            instance=instance,
            plan=plan,
            fingerprint=fingerprint,
            created_by=actor,
        )
        event(actor, receipt, "reserve")
        return receipt


def event(actor, receipt, action, result=AuditEvent.Result.SUCCESS, **context):
    audit.record(
        actor=actor,
        organization_id=receipt.instance.organization_id,
        action=f"app_instance.runtime.{action}",
        resource_type="app_instance",
        resource_id=receipt.instance_id,
        result=result,
        context=context,
    )


def execute(instance_id, actor):
    try:
        with transaction.atomic(durable=True):
            instance = AppInstance.objects.select_for_update().get(pk=instance_id)
            require_provision(actor, instance)
            receipt = RuntimeProvision.objects.select_for_update().get(instance=instance)
            if receipt.completed_at:
                return receipt
            if instance.archived:
                raise ValidationError("Archived instances cannot be provisioned.")
            if plan_runtime(actor, instance) != receipt.plan:
                raise RuntimeConflict()
            with transaction.atomic(using="tenant", durable=True):
                runtime_build.reconcile(receipt)
                database, bindings = runtime_build.build(receipt, actor)
            # Crash here leaves an unpublished, marked tenant schema. Retry
            # reconciles it. Ready catalog + mappings + audit commit together.
            receipt.database = database
            receipt.bindings = bindings
            receipt.completed_at = timezone.now()
            receipt.last_error = ""
            receipt.save(update_fields=["database", "bindings", "completed_at", "last_error"])
            event(actor, receipt, "ready", database_id=str(database.id))
        return receipt
    except Exception as exc:
        with transaction.atomic():
            # Same lock order as reservation/publication and receipt triggers.
            AppInstance.objects.select_for_update().filter(pk=instance_id).first()
            receipt = RuntimeProvision.objects.select_for_update().filter(instance_id=instance_id).first()
            if receipt and not receipt.completed_at:
                receipt.last_error = f"Provisioning failed ({type(exc).__name__}); retry or review required."
                receipt.save(update_fields=["last_error"])
                event(actor, receipt, "error", AuditEvent.Result.ERROR, error_type=type(exc).__name__)
        raise


def status(receipt):
    return {
        "instance_id": str(receipt.instance_id),
        "status": "ready" if receipt.completed_at else "failed" if receipt.last_error else "pending",
        "fingerprint": receipt.fingerprint,
        "database_id": str(receipt.database_id) if receipt.database_id else None,
        "bindings": receipt.bindings,
        "error": receipt.last_error,
        "completed_at": receipt.completed_at,
    }
