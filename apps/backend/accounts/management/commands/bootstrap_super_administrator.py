import getpass

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User
from permissions.services import assign_role


class Command(BaseCommand):
    help = (
        "Creates (or reuses) a User and grants them the platform-wide "
        "Super Administrator role. Run `seed_permissions` first."
    )

    def add_arguments(self, parser):
        parser.add_argument("email")

    @transaction.atomic
    def handle(self, *args, **options):
        email = User.objects.normalize_email(options["email"])
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            password = getpass.getpass("Password for new Super Administrator: ")
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                raise CommandError("Passwords did not match.")
            user = User.objects.create_user(email=email, password=password)
            self.stdout.write(f"Created user {email}")
        else:
            self.stdout.write(f"Reusing existing user {email}")

        assign_role(user=user, role_slug="super-administrator", organization=None)
        self.stdout.write(self.style.SUCCESS(f"{email} is now a platform-wide Super Administrator."))
