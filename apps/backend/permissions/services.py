"""
The single shared authorization service (ADR-0008). Every permission
check in the codebase — view, service, background task — goes through
`has_permission`, never an inline role-name check.
"""

from __future__ import annotations

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from audit import services as audit

from .catalog import ADMIN_PERMISSION_CODES, PLATFORM_WIDE_ROLE_SLUG
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
    # Only guards one *authenticated web actor* granting *another* user an
    # administrative role — CLI bootstrap (granted_by=None, an operator
    # with server access, trusted out-of-band) and a user's own
    # org-creation self-assignment (granted_by == user, the standard
    # "create an org, become its administrator" bootstrap flow) are both
    # deliberately exempt, or gateway mode would deadlock: a brand-new
    # user can't have MFA enabled before they even have an organization
    # to enroll for MFA within. See docs/architecture/ROADMAP.md Phase 10.
    if (
        settings.FEATURE_INTERNET_GATEWAY_ENABLED
        and granted_by is not None
        and granted_by.id != user.id
        and not user.mfa_enabled
        and role.permissions.filter(code__in=ADMIN_PERMISSION_CODES).exists()
    ):
        raise PermissionError_(
            f"Cannot assign {role_slug!r}: internet gateway mode requires the target user to "
            "have MFA enabled before an administrative role can be granted."
        )
    assignment = RoleAssignment.objects.create(
        user=user, role=role, organization=organization, granted_by=granted_by
    )
    audit.record(
        actor=granted_by,
        organization_id=organization.id if organization else None,
        action="permissions.role.assign",
        resource_type="user",
        resource_id=user.id,
        context={"role": role_slug},
    )
    return assignment


def get_role(slug: str) -> Role:
    return Role.objects.get(slug=slug, organization__isnull=True)


def permission_exists(code: str) -> bool:
    return Permission.objects.filter(code=code).exists()


def grant_resource_permission(
    *,
    user,
    permission_code: str,
    organization_id,
    resource_type: str,
    resource_id,
    granted_by=None,
    expires_at=None,
) -> ResourceGrant:
    """Central place fine-grained ResourceGrants are created — used by
    Phase 7 (restricting an Application's scope to specific resources)
    and reused by Phase 9 (sharing a single resource with a user/team).
    Same validate-then-create discipline as `assign_role`."""
    if not permission_exists(permission_code):
        raise PermissionError_(f"Unknown permission: {permission_code!r}")
    grant = ResourceGrant.objects.create(
        user=user,
        permission_id=permission_code,
        organization_id=organization_id,
        resource_type=resource_type,
        resource_id=resource_id,
        granted_by=granted_by,
        expires_at=expires_at,
    )
    audit.record(
        actor=granted_by,
        organization_id=organization_id,
        action="permissions.resource_grant.create",
        resource_type=resource_type,
        resource_id=resource_id,
        context={"permission": permission_code, "granted_to": str(user.id)},
    )
    return grant
