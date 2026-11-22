"""The owner's phone approver (ADR-0026, decision 6), made from the shop PC (Control Center > Settings > Owner).

    python manage.py approver_account create --email approver@shop --organization <id or slug>
                                             [--role pay-supervisor] [--name "Owner phone"] --base-url https://...
    python manage.py approver_account link --email approver@shop --base-url https://...   (a new link; the old ends)

Makes an account with NO password, inactive, a member of the organization with the chosen role, and prints a
single-use link (72 hours). The owner opens the link on the shop PC and creates a passkey on their phone; the account
then signs in with that phone only (passkey-only). Nobody, including whoever runs this, ever knows a password for it.
Maker/checker then has two accounts: that is two devices, not two people -- the audit log shows both.
"""

import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts import links
from accounts.models import User
from audit import services as audit
from organizations.models import Membership, Organization
from permissions.catalog import ORGANIZATION_ROLE_SUMMARIES
from permissions.services import assign_role


def _base(value: str) -> str:
    if not re.fullmatch(r"https://[A-Za-z0-9.\-]+(:\d{1,5})?", value or ""):
        raise CommandError("--base-url must be like https://localhost:8443")
    return value


class Command(BaseCommand):
    help = "Create the owner's phone approver account (passkey-only), or give it a new link."

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["create", "link"])
        parser.add_argument("--email", required=True)
        parser.add_argument("--organization", default="")
        parser.add_argument("--role", default="pay-supervisor")
        parser.add_argument("--name", default="Owner phone approver")
        parser.add_argument("--base-url", required=True)

    def handle(self, *args, **opts):
        base = _base(opts["base_url"])
        email = User.objects.normalize_email(opts["email"].strip())
        if not re.fullmatch(r"[^@\s]+@[^@\s]+", email):
            raise CommandError("Enter an email-like name for the account, e.g. approver@shop.")
        if opts["action"] == "link":
            user = User.objects.filter(email__iexact=email).first()
            if user is None:
                raise CommandError(f"No account {email}.")
            if user.is_active:
                raise CommandError(f"{email} is already active: sign in with its phone passkey.")
            token = links.issue(user=user, created_by=None)
            self.stdout.write(links.url(base, token))
            return

        role = opts["role"]
        if role not in ORGANIZATION_ROLE_SUMMARIES:
            raise CommandError(f"Unknown role {role}. For approving Pay credits use pay-supervisor.")
        ref = opts["organization"].strip()
        org = Organization.objects.filter(slug=ref).first()
        if org is None and re.fullmatch(r"[0-9a-fA-F-]{36}", ref):
            org = Organization.objects.filter(pk=ref).first()
        if org is None and not ref:
            # The shop PC usually has exactly one organization a person made (the built-in catalogue's is IntraForge's).
            mine = list(Organization.objects.exclude(created_by__email__iendswith="@service.internal")[:2])
            org = mine[0] if len(mine) == 1 else None
        if org is None:
            raise CommandError("Name the organization (--organization, its id or slug).")
        if User.objects.filter(email__iexact=email).exists():
            raise CommandError(f"An account {email} already exists. Choose another name.")
        with transaction.atomic():
            first, _, last = opts["name"].strip().partition(" ")
            user = User.objects.create_user(email=email, password=None, first_name=first[:150], last_name=last[:150])
            user.is_active = False
            user.job_title = "Phone approver"
            user.save(update_fields=["is_active", "job_title"])
            Membership.objects.create(user=user, organization=org, status=Membership.Status.ACTIVE)
            assign_role(user=user, role_slug=role, organization=org, granted_by=None)
            audit.record(
                actor=None,
                organization_id=org.id,
                action="account.approver.create",
                resource_type="user",
                resource_id=user.id,
                context={"role": role, "made_at": "shop PC (Control Center)"},
            )
            token = links.issue(user=user, created_by=None, organization_id=org.id)
        self.stdout.write(links.url(base, token))
