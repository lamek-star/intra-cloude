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
