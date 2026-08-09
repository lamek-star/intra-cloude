from django.db import transaction
from django.http import Http404
from django.utils.text import slugify

from permissions.services import assign_role

from .models import Membership, Organization, Team


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


def get_member_team(user, team_id) -> Team:
    """Same isolation discipline as get_member_organization: 404, not 403,
    if the requester isn't an active member of the owning organization."""
    try:
        return Team.objects.select_related("organization").get(
            id=team_id,
            organization__memberships__user=user,
            organization__memberships__status=Membership.Status.ACTIVE,
        )
    except Team.DoesNotExist as exc:
        raise Http404 from exc


def add_team_member(*, team: Team, user) -> Membership:
    """A user's Team is a single field on their (user, organization)
    Membership row (one team per membership — see organizations/models.py)
    rather than a many-to-many, so "adding" someone to a team is a
    membership update, not a new row."""
    try:
        membership = Membership.objects.get(user=user, organization=team.organization)
    except Membership.DoesNotExist as exc:
        raise Http404 from exc
    membership.team = team
    membership.save(update_fields=["team"])
    return membership


def remove_team_member(*, team: Team, user) -> Membership:
    try:
        membership = Membership.objects.get(user=user, organization=team.organization, team=team)
    except Membership.DoesNotExist as exc:
        raise Http404 from exc
    membership.team = None
    membership.save(update_fields=["team"])
    return membership
