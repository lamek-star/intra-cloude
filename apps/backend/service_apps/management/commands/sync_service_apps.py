from django.core.management.base import BaseCommand, CommandError

from service_apps import provisioning, services
from service_apps.deployments import all_deployments


class Command(BaseCommand):
    help = (
        "Idempotent start-up step for service applications (ADR-0018): each configured deployment's "
        "database role exists with the configured password, and its installed instance's schema is "
        "owned by that role. Run after migrate, and before restoring a tenant-database backup on a "
        "new computer (the restore needs the role to exist)."
    )

    def handle(self, *args, **options):
        deployments = all_deployments()
        if not deployments:
            self.stdout.write("No service applications are configured.")
            return
        for deployment in deployments.values():
            try:
                app = services.sync_deployment(deployment)
            except provisioning.ProvisioningError as exc:
                raise CommandError(f"{deployment.key}: {exc}") from exc
            state = f"installed as {app.display_name!r}" if app else "not installed yet"
            self.stdout.write(f"{deployment.key}: role {deployment.db_role} ready; {state}")
