from django.http import Http404
from rest_framework.exceptions import PermissionDenied

from audit import services as audit
from audit.models import AuditEvent
from organizations.services import get_member_organization
from permissions.services import has_permission

# The resource_type string ResourceGrant rows use for a per-instance
# capability check (see require_manage below) -- named here, not just
# inlined, so sharing/services.py can import it rather than hand-typing
# the string across an app boundary.
RESOURCE_TYPE_APP_INSTANCE = "app_instance"

# Phase 7 ("module scope"): a ResourceGrant/ShareGrant naming a single
# ModelDefinition rather than the whole tenant database (RESOURCE_TYPE_
# TENANT_DATABASE, already usable today) or the whole instance's metadata
# (RESOURCE_TYPE_APP_INSTANCE above). Checked as an alternative to, never
# instead of, the existing database-level grant in records.py::_require.
RESOURCE_TYPE_APP_MODEL = "app_model"


def check(actor, organization_id, capability, resource=None):
    # A service-account actor (bearer-token `Application`) is deliberately
    # NOT excluded here -- see FoundationView.service_account_methods
    # (views.py) for which endpoints a bearer token can reach at all; once
    # reachable, authorization is exactly this same deny-by-default
    # has_permission() check every human session goes through, never a
    # looser one. Nothing below grants anything a RoleAssignment/
    # ResourceGrant didn't already explicitly name.
    if not actor or not actor.is_authenticated or not actor.is_active:
        raise PermissionDenied("An active session is required.")
    get_member_organization(actor, organization_id)
    if not has_permission(actor, capability, organization_id=organization_id, resource=resource):
        audit.record(
            actor=actor,
            organization_id=organization_id,
            action=capability,
            resource_type=resource[0] if resource else "organization",
            resource_id=resource[1] if resource else organization_id,
            result=AuditEvent.Result.DENIED,
        )
        raise PermissionDenied("Required capability is not granted.")


def get_owned(model, object_id, actor, organization_path):
    # See check()'s comment above -- same reasoning, same deliberate
    # non-exclusion of service accounts.
    if not actor.is_authenticated or not actor.is_active:
        raise PermissionDenied("An active session is required.")
    try:
        return model.objects.get(
            **{
                "pk": object_id,
                f"{organization_path}__memberships__user": actor,
                f"{organization_path}__memberships__status": "active",
            }
        )
    except model.DoesNotExist as exc:
        raise Http404 from exc


def require_manage(actor, instance, schema=True):
    """Lives here (not instances.py) so schema_evolution.py can depend on
    it without an instances.py <-> schema_evolution.py import cycle."""
    check(
        actor,
        instance.organization_id,
        "app_instance.schema.manage" if schema else "app_instance.manage",
        ("app_instance", instance.id),
    )


def environment_scope_denied(request, model) -> bool:
    """Phase 10: True if this request must be denied -- authenticated via
    an Environment-scoped `ApplicationCredential` (environments app,
    Phase 22) whose Environment doesn't match the one this model's own
    instance's runtime database is bound to. Mirrors `databases/
    views.py::_environment_scope_denied` exactly (same
    `environments.services.check_environment_scope` call, same "only
    ever restricts credential-authenticated requests" behavior) -- before
    this function, app_platform's record/attachment endpoints were the
    one bearer-token-reachable surface in this codebase with no
    Environment-scope check at all, letting a Development-scoped
    credential reach any instance's records regardless of which
    Environment (if any) its runtime database was actually bound to.

    An instance with no completed `RuntimeProvision`, or one whose
    database has no Environment binding at all, has nothing to check
    against -- left as `False` (not denied) here; `records.py`/
    `attachments.py`'s own 404/403 already explain the former, and an
    unbound database is simply not reachable through *any*
    Environment-scoped credential regardless (the same "explicit binding
    required" rule `check_environment_scope` itself documents)."""
    from .models import RuntimeProvision

    receipt = RuntimeProvision.objects.filter(instance=model.instance).select_related("database").first()
    if receipt is None or receipt.database_id is None:
        return False
    from environments.services import check_environment_scope

    return not check_environment_scope(request, tenant_database=receipt.database)
