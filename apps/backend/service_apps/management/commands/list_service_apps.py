import json

from django.core.management.base import BaseCommand

from service_apps.deployments import all_deployments
from service_apps.models import ServiceApp
from service_apps.types import get_type


class Command(BaseCommand):
    help = (
        "Lists the installed service applications (no secrets) -- for the Windows Control Center's "
        "Applications panel, which has no IntraForge sign-in of its own."
    )

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", dest="as_json")

    def handle(self, *args, **options):
        deployments = all_deployments()
        rows = []
        for app in ServiceApp.objects.select_related("organization").order_by("display_name"):
            deployment = deployments.get(app.deployment)
            rows.append(
                {
                    "id": str(app.id),
                    "display_name": app.display_name,
                    "app_type": app.app_type,
                    "product": get_type(app.app_type).product_name,
                    "organization": app.organization.name,
                    "enabled": app.enabled,
                    "removed": app.removed_at is not None,
                    "launch_path": deployment.launch_path if deployment else None,
                    "open_path": f"/service-apps/{app.id}/open",
                    "reported_version": app.reported_version,
                    "last_seen_at": app.last_seen_at.isoformat() if app.last_seen_at else None,
                }
            )
        taken = set(ServiceApp.objects.values_list("deployment", flat=True))
        available = [
            {"deployment": d.key, "product": d.app_type.product_name}
            for d in deployments.values()
            if d.key not in taken
        ]
        if options["as_json"]:
            self.stdout.write(json.dumps({"installed": rows, "available": available}))
            return
        for r in rows:
            state = "removed" if r["removed"] else ("enabled" if r["enabled"] else "disabled")
            self.stdout.write(f"{r['display_name']} ({r['product']}, {r['organization']}): {state}")
        if not rows:
            self.stdout.write("No applications installed.")
