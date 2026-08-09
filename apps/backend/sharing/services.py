"""
Internal resource sharing (Phase 9, ADR-0008): grants a User/Team/
Organization read/write/admin-level access to exactly one resource by
creating the underlying `ResourceGrant`(s) that `permissions.services.
has_permission` already knows how to check — the same mechanism Phase 7
uses to scope an Application's access to one resource
(permissions/models.py's `ResourceGrant` docstring). `ShareGrant` is the
human-facing "who shared what with whom" record; it is not a second
enforcement path.

Known, documented limitation: sharing with a Team or "the organization"
materializes a `ResourceGrant` per member active *at share-creation
time*. A member who joins afterward does not retroactively gain access,
and revoking the share is best-effort against *current* membership (a
member who already left the team/org before the share is revoked keeps
whatever `ResourceGrant` they were given until it expires or is cleaned
up separately). This mirrors an existing, pre-Phase-9 property of this
codebase: `RoleAssignment` is likewise never automatically revoked when
a `Membership` is removed (docs/architecture/ROADMAP.md Phase 9).
"""

import uuid

from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import Http404
from django.utils import timezone

from accounts.models import User
from audit import services as audit
from audit.models import AuditEvent
from databases.connections import RESOURCE_TYPE_CONNECTED_DATABASE
from databases.models import ConnectedDatabase, TenantDatabase
from databases.views import RESOURCE_TYPE_TENANT_DATABASE
from organizations.models import Membership, Organization, Team
from permissions.models import ResourceGrant
from permissions.services import PermissionError_, grant_resource_permission, has_permission
from storage.models import Bucket
from storage.views import RESOURCE_TYPE_BUCKET

from .models import ShareGrant


class SharingPermissionDenied(Exception):
    pass


class SharingValidationError(Exception):
    pass


LEVEL_PERMISSIONS: dict[str, dict[str, list[str]]] = {
    RESOURCE_TYPE_BUCKET: {
        ShareGrant.Level.READ: ["storage.read"],
        ShareGrant.Level.WRITE: ["storage.read", "storage.write"],
        ShareGrant.Level.ADMIN: [
            "storage.read",
            "storage.write",
            "storage.delete",
            "storage.share",
            "storage.manage",
        ],
    },
    RESOURCE_TYPE_TENANT_DATABASE: {
        ShareGrant.Level.READ: ["database.read"],
        ShareGrant.Level.WRITE: ["database.read", "database.write"],
        ShareGrant.Level.ADMIN: ["database.read", "database.write", "dataset.export"],
    },
    RESOURCE_TYPE_CONNECTED_DATABASE: {
        # Connected mode is read-only by design (ADR-0009 Final
        # Recommendation, Phase 8) — no write/admin level to grant.
        ShareGrant.Level.READ: ["database.read"],
    },
}

_RESOURCE_ORG_FILTERS = {
    RESOURCE_TYPE_BUCKET: lambda resource_id, org_id: Bucket.objects.filter(
        id=resource_id, project__workspace__organization_id=org_id
    ).exists(),
    RESOURCE_TYPE_TENANT_DATABASE: lambda resource_id, org_id: TenantDatabase.objects.filter(
        id=resource_id, project__workspace__organization_id=org_id
    ).exists(),
    RESOURCE_TYPE_CONNECTED_DATABASE: lambda resource_id, org_id: ConnectedDatabase.objects.filter(
        id=resource_id, project__workspace__organization_id=org_id
    ).exists(),
}


def _require(actor, permission_code, organization_id, *, action, resource_id, request_id):
    if not has_permission(actor, permission_code, organization_id=organization_id):
        audit.record(
            actor=actor,
            organization_id=organization_id,
            action=action,
            resource_type="share_grant",
            resource_id=resource_id,
            request_id=request_id,
            result=AuditEvent.Result.DENIED,
        )
        raise SharingPermissionDenied(f"{permission_code} required")


def get_member_share(user, share_id) -> ShareGrant:
    try:
        return ShareGrant.objects.select_related("organization").get(
            id=share_id,
            organization__memberships__user=user,
            organization__memberships__status=Membership.Status.ACTIVE,
        )
    except ShareGrant.DoesNotExist as exc:
        raise Http404 from exc


def _principal_user_ids(principal_type: str, *, user=None, team: Team | None = None, organization=None):
    if principal_type == ShareGrant.PrincipalType.USER:
        return [user.id]
    if principal_type == ShareGrant.PrincipalType.TEAM:
        return list(
            Membership.objects.filter(team=team, status=Membership.Status.ACTIVE).values_list(
                "user_id", flat=True
            )
        )
    if principal_type == ShareGrant.PrincipalType.ORGANIZATION:
        return list(
            Membership.objects.filter(
                organization=organization, status=Membership.Status.ACTIVE
            ).values_list("user_id", flat=True)
        )
    raise SharingValidationError(f"unsupported principal_type: {principal_type!r}")


def create_share_grant(
    *,
    actor,
    organization: Organization,
    resource_type: str,
    resource_id,
    principal_type: str,
    level: str,
    user=None,
    team: Team | None = None,
    expires_at=None,
    request_id: str = "",
) -> ShareGrant:
    _require(
        actor, "sharing.manage", organization.id, action="sharing.create", resource_id=resource_id,
        request_id=request_id,
    )

    if resource_type not in LEVEL_PERMISSIONS:
        raise SharingValidationError(f"unsupported resource_type: {resource_type!r}")
    if level not in LEVEL_PERMISSIONS[resource_type]:
        raise SharingValidationError(f"level {level!r} is not supported for {resource_type!r}")
    if not _RESOURCE_ORG_FILTERS[resource_type](resource_id, organization.id):
        raise SharingValidationError("resource not found in this organization")

    if principal_type == ShareGrant.PrincipalType.USER:
        if user is None:
            raise SharingValidationError("user is required for a user-level share")
        if not Membership.objects.filter(
            user=user, organization=organization, status=Membership.Status.ACTIVE
        ).exists():
            raise SharingValidationError("user is not an active member of this organization")
    elif principal_type == ShareGrant.PrincipalType.TEAM:
        if team is None or team.organization_id != organization.id:
            raise SharingValidationError("team must belong to this organization")
    elif principal_type == ShareGrant.PrincipalType.ORGANIZATION:
        pass
    else:
        raise SharingValidationError(f"unsupported principal_type: {principal_type!r}")

    target_users = list(
        User.objects.filter(
            id__in=_principal_user_ids(principal_type, user=user, team=team, organization=organization)
        )
    )

    with transaction.atomic():
        share = ShareGrant.objects.create(
            id=uuid.uuid4(),
            organization=organization,
            resource_type=resource_type,
            resource_id=resource_id,
            principal_type=principal_type,
            user=user,
            team=team,
            level=level,
            expires_at=expires_at,
            created_by=actor,
        )
        for permission_code in LEVEL_PERMISSIONS[resource_type][level]:
            for target_user in target_users:
                try:
                    with transaction.atomic():
                        grant_resource_permission(
                            user=target_user,
                            permission_code=permission_code,
                            organization_id=organization.id,
                            resource_type=resource_type,
                            resource_id=resource_id,
                            granted_by=actor,
                            expires_at=expires_at,
                        )
                except IntegrityError:
                    # Already granted (e.g. an overlapping earlier share,
                    # or Phase 7 application scoping on the same
                    # resource/user/permission) — sharing is additive, so
                    # this is not an error.
                    pass
                except PermissionError_ as exc:
                    raise SharingValidationError(str(exc)) from exc

    audit.record(
        actor=actor,
        organization_id=organization.id,
        action="sharing.create",
        resource_type="share_grant",
        resource_id=share.id,
        request_id=request_id,
        context={
            "resource_type": resource_type,
            "resource_id": str(resource_id),
            "principal_type": principal_type,
            "level": level,
        },
    )
    return share


def revoke_share_grant(*, actor, share: ShareGrant, request_id: str = "") -> None:
    _require(
        actor,
        "sharing.manage",
        share.organization_id,
        action="sharing.revoke",
        resource_id=share.resource_id,
        request_id=request_id,
    )

    target_user_ids = _principal_user_ids(
        share.principal_type, user=share.user, team=share.team, organization=share.organization
    )
    permission_codes = LEVEL_PERMISSIONS[share.resource_type][share.level]
    ResourceGrant.objects.filter(
        user_id__in=target_user_ids,
        permission_id__in=permission_codes,
        organization=share.organization,
        resource_type=share.resource_type,
        resource_id=share.resource_id,
    ).delete()

    share.revoked_at = timezone.now()
    share.save(update_fields=["revoked_at"])

    audit.record(
        actor=actor,
        organization_id=share.organization_id,
        action="sharing.revoke",
        resource_type="share_grant",
        resource_id=share.id,
        request_id=request_id,
    )


def set_external_sharing_enabled(
    *, actor, organization: Organization, enabled: bool, request_id: str = ""
) -> Organization:
    _require(
        actor, "sharing.manage", organization.id, action="sharing.external.toggle", resource_id="",
        request_id=request_id,
    )
    if enabled and not settings.FEATURE_EXTERNAL_SHARING_ENABLED:
        raise SharingValidationError(
            "external sharing is disabled for this deployment "
            "(FEATURE_EXTERNAL_SHARING_ENABLED is off) and cannot be enabled per-organization"
        )

    organization.external_sharing_enabled = enabled
    organization.save(update_fields=["external_sharing_enabled"])

    audit.record(
        actor=actor,
        organization_id=organization.id,
        action="sharing.external.enable" if enabled else "sharing.external.disable",
        resource_type="organization",
        resource_id=organization.id,
        request_id=request_id,
    )
    return organization
