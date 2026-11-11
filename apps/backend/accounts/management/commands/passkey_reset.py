from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User
from audit import services as audit


class Command(BaseCommand):
    """Recovery when every passkey of an account is lost (ADR-0019). It runs only on the server itself
    (physical access to the shop PC is the trust anchor, as for the keys file): password sign-in is allowed
    again, and with --remove-all the account's passkeys are deleted too."""

    help = "Allows password sign-in again for an account that signs in with passkeys only."

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument(
            "--remove-all", action="store_true", help="Also delete all of the account's passkeys."
        )

    @transaction.atomic
    def handle(self, *args, **options):
        user = User.objects.filter(email__iexact=User.objects.normalize_email(options["email"])).first()
        if user is None:
            raise CommandError("No account with that email.")
        removed = 0
        if options["remove_all"]:
            removed, _ = user.passkeys.all().delete()
        user.passkey_only = False
        user.save(update_fields=["passkey_only"])
        audit.record(
            actor=None,
            organization_id=None,
            action="passkey.reset",
            resource_type="user",
            resource_id=user.id,
            context={"removed": removed, "by": "server command"},
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"{user.email} can sign in with the password again"
                + (f"; {removed} passkey(s) removed." if removed else ".")
            )
        )
