"""The installation's Super Administrators, managed from the shop PC (the Control Center's "Owner" card).

    python manage.py super_administrators list [--json]
    python manage.py super_administrators grant <email>
    python manage.py super_administrators revoke <email>

Only someone at the shop PC can run this (it needs the Docker containers), which is why it is the way to hand out the
top level: no web page grants it, and the first account to sign up is never made one automatically (anyone on the
shop network could have signed up first). Only existing, active people: never a service account (an application's
identity). The last Super Administrator cannot be removed here either, so the installation is never left without one
once it has one. Every change is in the audit log.
"""

import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User
from audit import services as audit
from permissions.models import RoleAssignment
from permissions.services import assign_role

ROLE = "super-administrator"
# IntraForge's own identities (applications' service accounts, the catalogue import) use this reserved domain.
INTERNAL_DOMAIN = "@service.internal"


def _holders() -> set:
    return set(
        RoleAssignment.objects.filter(role__slug=ROLE, organization__isnull=True).values_list("user_id", flat=True)
    )


def _person(email: str) -> User:
    user = User.objects.filter(email__iexact=User.objects.normalize_email(email.strip())).first()
    if user is None:
        raise CommandError(f"No account with the email {email}. The person signs up (or is added) first.")
    if hasattr(user, "service_account") or user.email.lower().endswith(INTERNAL_DOMAIN):
        raise CommandError(f"{user.email} is an application's account, not a person.")
    if not user.is_active:
        raise CommandError(f"{user.email} is switched off. Switch the account on first.")
    return user


class Command(BaseCommand):
    help = "List, grant or remove the installation-wide Super Administrator role (run on the shop PC)."

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest="action", required=True)
        listing = sub.add_parser("list", help="Every active person, and who is a Super Administrator.")
        listing.add_argument("--json", action="store_true")
        for name in ("grant", "revoke"):
            sub.add_parser(name).add_argument("email")

    def handle(self, *args, **options):
        action = options["action"]
        if action == "list":
            self._list(options.get("json", False))
            return
        user = _person(options["email"])
        with transaction.atomic():
            holders = _holders()
            if action == "grant":
                if user.pk in holders:
                    self.stdout.write(f"{user.email} is already a Super Administrator.")
                    return
                assign_role(user=user, role_slug=ROLE, organization=None)
            else:
                if user.pk not in holders:
                    self.stdout.write(f"{user.email} is not a Super Administrator.")
                    return
                if len(holders) == 1:
                    raise CommandError(
                        "This is the only Super Administrator. Make someone else one first, then remove this one."
                    )
                RoleAssignment.objects.filter(user=user, role__slug=ROLE, organization__isnull=True).delete()
            audit.record(
                actor=None,
                organization_id=None,
                action=f"system.super_administrator.{action}",
                resource_type="user",
                resource_id=user.id,
                context={"email": user.email, "by": "the shop PC (Control Center)"},
            )
        done = "is now a Super Administrator" if action == "grant" else "is no longer a Super Administrator"
        self.stdout.write(self.style.SUCCESS(f"{user.email} {done}."))

    def _list(self, as_json: bool) -> None:
        holders = _holders()
        people = [
            {
                "email": u.email,
                "name": f"{u.first_name} {u.last_name}".strip(),
                "super_administrator": u.pk in holders,
            }
            for u in User.objects.filter(is_active=True, service_account__isnull=True)
            .exclude(email__iendswith=INTERNAL_DOMAIN)
            .order_by("email")
        ]
        if as_json:
            self.stdout.write(json.dumps(people))
            return
        for p in people:
            mark = "  [Super Administrator]" if p["super_administrator"] else ""
            self.stdout.write(f"{p['email']}  {p['name']}{mark}")
