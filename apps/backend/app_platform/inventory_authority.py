"""Business-operation authority over an installed application's stock (ADR-0017).

Four stable, default-deny capabilities -- `inventory.sell`, `inventory.receive`, `inventory.adjust`,
`inventory.transfer` -- answer exactly one question: "may this actor perform THIS kind of stock-changing
operation in THIS installed application?" They are checked with the ordinary `has_permission`, so a grant is
either a role (organization-wide) or a `ResourceGrant`/`ShareGrant` on the AppInstance (resource type
`inventory_operations`); no role name is ever consulted (ADR-0008).

They deliberately do not overlap: the right to sell is not the right to receive, adjust or transfer, and the
reverse. Which records an operation may touch is still decided by the existing per-model grants; which
inventory transitions are valid is still decided by the PostgreSQL quantity ledger. This module only answers
the first question.
"""

from audit import services as audit
from audit.models import AuditEvent
from permissions.services import has_permission

# The resource_type tag ResourceGrant/ShareGrant rows use for these grants; the resource id is the
# AppInstance.
RESOURCE_TYPE_INVENTORY_OPERATIONS = "inventory_operations"

SELL = "inventory.sell"
RECEIVE = "inventory.receive"
ADJUST = "inventory.adjust"
TRANSFER = "inventory.transfer"
OPERATIONS = frozenset({SELL, RECEIVE, ADJUST, TRANSFER})


class OperationDenied(Exception):
    """The actor does not hold the named business-operation authority."""


def holds(actor, instance, permission: str) -> bool:
    if permission not in OPERATIONS:
        raise ValueError(f"not a business-operation capability: {permission!r}")
    return has_permission(
        actor,
        permission,
        organization_id=instance.organization_id,
        resource=(RESOURCE_TYPE_INVENTORY_OPERATIONS, instance.id),
    )


def require(actor, instance, permission: str, *, action: str) -> None:
    """Raises OperationDenied (and audits a `denied` event) unless the actor holds the authority. Evaluated on
    every call against current grants, so a revocation takes effect on the very next operation."""
    if holds(actor, instance, permission):
        return
    audit.record(
        actor=actor,
        organization_id=instance.organization_id,
        action=action,
        resource_type=RESOURCE_TYPE_INVENTORY_OPERATIONS,
        resource_id=instance.id,
        result=AuditEvent.Result.DENIED,
        context={"required": permission},
    )
    raise OperationDenied(f"{permission} required")
