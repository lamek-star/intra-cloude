from django.core.management.base import BaseCommand, CommandError

from system.tenant_role import TenantRoleError, ensure_role


class Command(BaseCommand):
    help = (
        "Idempotent variant of provision_tenant_role: creates the "
        "least-privilege tenant role if it doesn't exist, or updates its "
        "password if it does. Intended for scripted/automated "
        "provisioning steps (e.g. run once per deployment start) rather "
        "than interactive use — see system/tenant_role.py::ensure_role."
    )

    def add_arguments(self, parser):
        parser.add_argument("role_name")
        parser.add_argument("--password", required=True, help="Password for the role.")

    def handle(self, *args, **options):
        try:
            ensure_role(options["role_name"], options["password"])
        except TenantRoleError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Role {options['role_name']!r} is ready (CONNECT+CREATE on the tenant database only)."
            )
        )
