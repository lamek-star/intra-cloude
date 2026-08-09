import getpass

from django.core.management.base import BaseCommand, CommandError

from system.tenant_role import TenantRoleError, provision_role


class Command(BaseCommand):
    help = (
        "Creates a least-privilege PostgreSQL role for the tenant database "
        "(CONNECT + CREATE on that database only — never superuser; "
        "docs/security/THREAT_MODEL.md TB3). Run once using the existing "
        "bootstrap TENANT_DB_USER credentials; the app does not "
        "automatically switch to the new role — set TENANT_DB_USER/"
        "TENANT_DB_PASSWORD to it yourself once you've verified it works."
    )

    def add_arguments(self, parser):
        parser.add_argument("role_name")

    def handle(self, *args, **options):
        role_name = options["role_name"]
        password = getpass.getpass(f"Password for new role {role_name!r}: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            raise CommandError("Passwords did not match.")

        try:
            provision_role(role_name, password)
        except TenantRoleError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Role {role_name!r} created with CONNECT+CREATE on the tenant database only "
                "(not superuser, not CREATEDB, not CREATEROLE). Set TENANT_DB_USER/"
                "TENANT_DB_PASSWORD to this role's credentials to adopt it."
            )
        )
