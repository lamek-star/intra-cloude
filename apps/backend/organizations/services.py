from django.db import transaction
from django.http import Http404
from django.utils.text import slugify

from permissions.services import assign_role

from .models import Membership, Organization


def get_member_organization(user, organization_id) -> Organization:
    """Resolves an Organization only if the requester is an active member
    of it — otherwise 404 (not 403), so org existence isn't leaked to
    non-members (docs/security/THREAT_MODEL.md Section 4). This is the
    query every org-scoped view, in any app, goes through; it is the
    primary tenant-isolation defense, not a convenience."""
    try:
        return Organization.objects.get(
            id=organization_id,
            memberships__user=user,
            memberships__status=Membership.Status.ACTIVE,
        )
    except Organization.DoesNotExist as exc:
        raise Http404 from exc


def create_organization(*, name: str, created_by, slug: str | None = None) -> Organization:
    """Creates an Organization, makes the creator an active member, and
    grants them the Organization Administrator role — all in one
    transaction so an org can never exist without an owner able to manage
    it."""
    slug = slug or slugify(name)
    with transaction.atomic():
        org = Organization.objects.create(name=name, slug=slug, created_by=created_by)
        Membership.objects.create(
            user=created_by, organization=org, status=Membership.Status.ACTIVE
        )
        assign_role(
            user=created_by,
            role_slug="organization-administrator",
            organization=org,
            granted_by=created_by,
        )
    return org
