from django.db import transaction
from django.utils.text import slugify

from permissions.services import assign_role

from .models import Membership, Organization


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
