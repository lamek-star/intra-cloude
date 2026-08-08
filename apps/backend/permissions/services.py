"""
The single shared authorization service (ADR-0008). Every permission
check in the codebase — view, service, background task — goes through
`has_permission`, never an inline role-name check.
"""

from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from .catalog import PLATFORM_WIDE_ROLE_SLUG
from .models import Permission, ResourceGrant, Role, RoleAssignment


class PermissionError_(Exception):
    """Raised by service-layer assign_role when a caller asks for an
    invalid combination (e.g. a platform-wide assignment for a non-Super-
    Administrator role). Named with a trailing underscore to avoid
    shadowing the builtin PermissionError."""


def has_role_permission(user, permission_code: str, organization_id) -> bool:
    """Coarse-grained check: does the user hold a Role — assigned
    platform-wide (organization=None) or scoped to this organization —
    whose permission set includes `permission_code`?"""
    if not user or not user.is_authenticated:
        return False
    return RoleAssignment.objects.filter(
        Q(organization_id=organization_id) | Q(organization__isnull=True),
        user=user,
        role__permissions__code=permission_code,
    ).exists()


def has_resource_permission(
    user, permission_code: str, organization_id, resource_type: str, resource_id
) -> bool:
    """Fine-grained check: does the user hold a non-expired ResourceGrant
    for this exact permission on this exact resource?"""
    if not user or not user.is_authenticated:
        return False
    return ResourceGrant.objects.filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()),
        user=user,
        organization_id=organization_id,
        permission_id=permission_code,
        resource_type=resource_type,
        resource_id=resource_id,
    ).exists()


def has_permission(user, permission_code: str, organization_id=None, resource=None) -> bool:
    """The one entry point every authorization decision in the codebase
    should call. `resource`, if given, is (resource_type, resource_id).

    Effective permission = role-wide grant applicable to the organization
    OR a non-expired resource grant on the exact resource
    (docs/security/PERMISSIONS.md Section 4)."""
    if has_role_permission(user, permission_code, organization_id):
        return True
    if resource is not None:
        resource_type, resource_id = resource
        return has_resource_permission(
            user, permission_code, organization_id, resource_type, resource_id
        )
    return False


def get_user_organization_ids(user):
    """Organizations the user can act within via a role assignment (used
    to scope list/detail querysets — the primary IDOR/BOLA defense per
    docs/security/THREAT_MODEL.md Section 4)."""
    if not user or not user.is_authenticated:
        return set()
    return set(
        RoleAssignment.objects.filter(user=user, organization__isnull=False).values_list(
            "organization_id", flat=True
        )
    )


def assign_role(*, user, role_slug: str, organization=None, granted_by=None) -> RoleAssignment:
    """Central place role assignments are created, so the platform-wide
    restriction is enforced in exactly one place."""
    role = Role.objects.get(slug=role_slug, organization__isnull=True)
    if organization is None and role.slug != PLATFORM_WIDE_ROLE_SLUG:
        raise PermissionError_(
            f"Only the {PLATFORM_WIDE_ROLE_SLUG!r} role may be assigned platform-wide (organization=None)."
        )
    return RoleAssignment.objects.create(
        user=user, role=role, organization=organization, granted_by=granted_by
    )


def get_role(slug: str) -> Role:
    return Role.objects.get(slug=slug, organization__isnull=True)


def permission_exists(code: str) -> bool:
    return Permission.objects.filter(code=code).exists()
