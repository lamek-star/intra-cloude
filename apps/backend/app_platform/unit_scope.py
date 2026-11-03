"""Phase 7 Step 3 ("unit scope") service layer: grant/revoke a
UnitScopedGrant, and resolve which units (if any) an actor is restricted
to for a given model/capability -- the one function records.py actually
calls on every record operation."""

from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.utils import timezone

from audit import services as audit
from audit.models import AuditEvent
from org_units.models import OrganizationalUnit
from organizations.models import Membership
from permissions.services import has_permission

from .models import FieldDefinition, ModelDefinition, UnitScopedGrant

LEVEL_PERMISSIONS: dict[str, list[str]] = {
    UnitScopedGrant.Level.READ: ["database.read"],
    UnitScopedGrant.Level.WRITE: ["database.read", "database.write"],
}


class UnitScopeValidationError(Exception):
    pass


class UnitScopePermissionDenied(Exception):
    pass


def unit_reference_field(model: ModelDefinition) -> FieldDefinition | None:
    """The model's own single org_unit_reference field, or None if it has
    zero or more than one -- either way, "restricted to unit X" would be
    ambiguous or meaningless, so unit scoping doesn't apply."""
    fields = list(model.fields.filter(data_type=FieldDefinition.DataType.ORG_UNIT_REFERENCE))
    return fields[0] if len(fields) == 1 else None


def granted_unit_ids(user, model: ModelDefinition, capability: str) -> set:
    """Every unit id `user` is granted `capability` for, on this specific
    model, via a non-expired UnitScopedGrant. Empty if none -- callers
    treat that exactly like "no access", never like "unrestricted"."""
    levels = [level for level, perms in LEVEL_PERMISSIONS.items() if capability in perms]
    if not levels:
        return set()
    now = timezone.now()
    return set(
        UnitScopedGrant.objects.filter(model=model, user=user, level__in=levels)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .values_list("unit_id", flat=True)
    )


def get_member_grant(user, grant_id) -> UnitScopedGrant:
    """Same isolation discipline as every other get_member_* in this
    codebase: 404, not 403, if the requester isn't an active member of the
    owning organization (docs/security/THREAT_MODEL.md Section 4)."""
    try:
        return UnitScopedGrant.objects.select_related("model__instance").get(
            id=grant_id,
            model__instance__organization__memberships__user=user,
            model__instance__organization__memberships__status=Membership.Status.ACTIVE,
        )
    except UnitScopedGrant.DoesNotExist as exc:
        raise Http404 from exc


def _require_sharing_manage(actor, model: ModelDefinition, *, action: str) -> None:
    organization_id = model.instance.organization_id
    if not has_permission(actor, "sharing.manage", organization_id=organization_id):
        audit.record(
            actor=actor,
            organization_id=organization_id,
            action=action,
            resource_type="app_model",
            resource_id=model.id,
            result=AuditEvent.Result.DENIED,
        )
        raise UnitScopePermissionDenied("sharing.manage required")


def grant_unit_scope(
    *, actor, model: ModelDefinition, unit: OrganizationalUnit, user, level: str, expires_at=None
) -> UnitScopedGrant:
    _require_sharing_manage(actor, model, action="app_instance.unit_scope.grant")

    if unit.organization_id != model.instance.organization_id:
        raise UnitScopeValidationError("unit belongs to a different organization")
    if unit_reference_field(model) is None:
        raise UnitScopeValidationError(
            "this model needs exactly one org_unit_reference field before it can be unit-scoped"
        )
    if not Membership.objects.filter(
        user=user, organization=model.instance.organization, status=Membership.Status.ACTIVE
    ).exists():
        raise UnitScopeValidationError("user is not an active member of this organization")
    if level not in UnitScopedGrant.Level.values:
        raise UnitScopeValidationError(f"unsupported level: {level!r}")

    with transaction.atomic():
        grant, _created = UnitScopedGrant.objects.update_or_create(
            model=model,
            unit=unit,
            user=user,
            defaults={"level": level, "granted_by": actor, "expires_at": expires_at},
        )
    audit.record(
        actor=actor,
        organization_id=model.instance.organization_id,
        action="app_instance.unit_scope.grant",
        resource_type="app_model",
        resource_id=model.id,
        context={"unit": str(unit.id), "user": str(user.id), "level": level},
    )
    return grant


def revoke_unit_scope(*, actor, grant: UnitScopedGrant) -> None:
    model = grant.model
    _require_sharing_manage(actor, model, action="app_instance.unit_scope.revoke")
    grant_id, unit_id, user_id = grant.id, grant.unit_id, grant.user_id
    grant.delete()
    audit.record(
        actor=actor,
        organization_id=model.instance.organization_id,
        action="app_instance.unit_scope.revoke",
        resource_type="app_model",
        resource_id=model.id,
        context={"grant": str(grant_id), "unit": str(unit_id), "user": str(user_id)},
    )
