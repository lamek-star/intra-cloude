from django.db import transaction
from django.http import Http404

from audit import services as audit
from organizations.models import Membership

from .models import OrganizationalUnit, UnitMembership


class CycleError(Exception):
    """Raised when a create/reparent would make a unit its own ancestor."""


class CrossOrganizationError(Exception):
    """Raised when a parent belongs to a different organization."""


class HasChildrenError(Exception):
    """Raised when deleting a unit that still has child units."""


def get_member_unit(user, unit_id) -> OrganizationalUnit:
    """Same isolation discipline as organizations.services.get_member_team:
    404, not 403, if the requester isn't an active member of the owning
    organization (docs/security/THREAT_MODEL.md Section 4)."""
    try:
        return OrganizationalUnit.objects.select_related("organization").get(
            id=unit_id,
            organization__memberships__user=user,
            organization__memberships__status=Membership.Status.ACTIVE,
        )
    except OrganizationalUnit.DoesNotExist as exc:
        raise Http404 from exc


def _assert_no_cycle(*, organization_id, unit_id, parent: OrganizationalUnit) -> None:
    """Walks the proposed parent's ancestor chain looking for `unit_id`.
    Locks each row visited (select_for_update) so a concurrent reparent
    elsewhere in the same chain can't race this check -- must be called
    inside an outer transaction.atomic()."""
    if parent.organization_id != organization_id:
        raise CrossOrganizationError
    current = OrganizationalUnit.objects.select_for_update().get(id=parent.id)
    seen = set()
    while current is not None:
        if current.id == unit_id:
            raise CycleError
        if current.id in seen:
            # Defensive only -- an existing cycle would mean a prior bug,
            # not something a correct caller of this function can produce.
            raise CycleError
        seen.add(current.id)
        if current.parent_id is None:
            break
        current = OrganizationalUnit.objects.select_for_update().get(id=current.parent_id)


def create_unit(
    *, organization, name: str, unit_type: str, actor, parent: OrganizationalUnit | None = None
) -> OrganizationalUnit:
    with transaction.atomic():
        if parent is not None:
            if parent.organization_id != organization.id:
                raise CrossOrganizationError
            # A brand-new unit has no id yet, so it can never appear in its
            # own parent's ancestor chain -- no cycle is possible on create,
            # only on reparent. Locking the parent row here still protects
            # against it being deleted/reparented concurrently mid-creation.
            OrganizationalUnit.objects.select_for_update().get(id=parent.id)
        unit = OrganizationalUnit.objects.create(
            organization=organization,
            parent=parent,
            name=name,
            unit_type=unit_type,
            created_by=actor,
        )
        audit.record(
            actor=actor,
            organization_id=organization.id,
            action="org_unit.create",
            resource_type="org_unit",
            resource_id=unit.id,
            context={"name": name, "unit_type": unit_type, "parent": str(parent.id) if parent else None},
        )
        return unit


def update_unit(
    *,
    unit: OrganizationalUnit,
    actor,
    name: str | None = None,
    unit_type: str | None = None,
    parent: OrganizationalUnit | None | object = None,
    parent_given: bool = False,
) -> OrganizationalUnit:
    """`parent`/`parent_given` distinguish "not passed" from "explicitly
    set to null" (move to root) -- a plain `parent=None` default can't
    express that distinction."""
    update_fields = []
    with transaction.atomic():
        locked = OrganizationalUnit.objects.select_for_update().get(id=unit.id)
        if name is not None:
            locked.name = name
            update_fields.append("name")
        if unit_type is not None:
            locked.unit_type = unit_type
            update_fields.append("unit_type")
        if parent_given:
            if parent is not None:
                _assert_no_cycle(organization_id=locked.organization_id, unit_id=locked.id, parent=parent)
            locked.parent = parent
            update_fields.append("parent")
        if update_fields:
            locked.save(update_fields=update_fields)
            audit.record(
                actor=actor,
                organization_id=locked.organization_id,
                action="org_unit.update",
                resource_type="org_unit",
                resource_id=locked.id,
                context={"fields": update_fields},
            )
        return locked


def delete_unit(*, unit: OrganizationalUnit, actor) -> None:
    with transaction.atomic():
        locked = OrganizationalUnit.objects.select_for_update().get(id=unit.id)
        if locked.children.exists():
            raise HasChildrenError
        organization_id = locked.organization_id
        unit_id = locked.id
        locked.delete()
        audit.record(
            actor=actor,
            organization_id=organization_id,
            action="org_unit.delete",
            resource_type="org_unit",
            resource_id=unit_id,
            context={},
        )


def add_unit_member(*, unit: OrganizationalUnit, user, actor) -> UnitMembership:
    if not Membership.objects.filter(
        user=user, organization=unit.organization, status=Membership.Status.ACTIVE
    ).exists():
        raise Http404
    membership, created = UnitMembership.objects.get_or_create(
        unit=unit, user=user, defaults={"created_by": actor}
    )
    if created:
        audit.record(
            actor=actor,
            organization_id=unit.organization_id,
            action="org_unit.membership.add",
            resource_type="org_unit",
            resource_id=unit.id,
            context={"user": str(user.id)},
        )
    return membership


def remove_unit_member(*, unit: OrganizationalUnit, user, actor) -> None:
    try:
        membership = UnitMembership.objects.get(unit=unit, user=user)
    except UnitMembership.DoesNotExist as exc:
        raise Http404 from exc
    membership.delete()
    audit.record(
        actor=actor,
        organization_id=unit.organization_id,
        action="org_unit.membership.remove",
        resource_type="org_unit",
        resource_id=unit.id,
        context={"user": str(user.id)},
    )
