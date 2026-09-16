"""
`python manage.py seed_reference_app --template <key> --organization
    <id-or-slug> --actor-email <email> [--project <id>] [--provision]`

Phase 8 (docs/implementation/APP_PLATFORM_ROADMAP.md,
docs/implementation/APP_PLATFORM_PHASE8.md): a generic version of Phase
4's `seed_spare_parts_reference_app` command, publishing any
`app_platform.reference_templates.REGISTRY` entry into a real, existing
organization (never invents one), using the same
`templates.create_template`/`publish_template` service calls the App
Builder UI itself uses. `--template` accepts any registry key, including
`spare_parts` -- the two commands are equivalent for that one template;
`seed_spare_parts_reference_app` is kept as-is for backward compatibility
rather than removed.

`--actor-email` must name a real user who already has `app_template.manage`
(and, with `--project`/`--provision`, `app_instance.manage`) in that
organization -- this command is a thin wrapper around the same permission-
checked service layer everything else goes through, not a bypass.

Idempotent: reuses an existing, non-archived template with the same label
in that organization rather than creating a duplicate on repeat runs.
`--project` additionally installs it (`instances.install`); `--provision`
(requires `--project`) also plans and provisions the runtime, so a single
command can stand up a fully working demo instance.
"""

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from accounts.models import User
from app_platform import instances, provisioning, templates
from app_platform.models import AppTemplate
from app_platform.reference_templates import REGISTRY
from app_platform.runtime_plan import plan_runtime
from organizations.models import Organization
from workspaces.models import Project


class Command(BaseCommand):
    help = "Publishes a Phase 8 (or Phase 4) reference AppTemplate into a real organization."

    def add_arguments(self, parser):
        parser.add_argument(
            "--template", required=True, choices=sorted(REGISTRY),
            help="Reference template registry key.",
        )
        parser.add_argument("--organization", required=True, help="Organization id (UUID) or slug.")
        parser.add_argument("--actor-email", required=True, help="Email of the user performing this action.")
        parser.add_argument("--project", default=None, help="Project id to also install the template into.")
        parser.add_argument(
            "--provision", action="store_true",
            help="Also plan and provision the runtime (requires --project).",
        )

    def handle(self, *args, **options):
        entry = REGISTRY[options["template"]]
        label, builder = entry["label"], entry["builder"]

        organization = self._resolve_organization(options["organization"])
        try:
            actor = User.objects.get(email=options["actor_email"])
        except User.DoesNotExist as exc:
            raise CommandError(f"No such user: {options['actor_email']}") from exc

        if options["provision"] and not options["project"]:
            raise CommandError("--provision requires --project.")

        template = AppTemplate.objects.filter(organization=organization, label=label, archived=False).first()
        if template is None:
            template = templates.create_template(actor, organization, {"label": label, "draft": builder()})
            self.stdout.write(self.style.SUCCESS(f"Created template {template.id}"))
        else:
            self.stdout.write(f"Reusing existing template {template.id}")

        version = template.versions.order_by("-number").first()
        if version is None:
            version = templates.publish_template(actor, template)
            self.stdout.write(self.style.SUCCESS(f"Published version {version.number}"))
        else:
            self.stdout.write(f"Reusing existing version {version.number}")

        if not options["project"]:
            return

        try:
            project = Project.objects.get(pk=options["project"], workspace__organization=organization)
        except Project.DoesNotExist as exc:
            raise CommandError(f"No such project in this organization: {options['project']}") from exc

        instance = instances.install(actor, project, {"label": label, "template_version": str(version.id)})
        self.stdout.write(self.style.SUCCESS(f"Installed instance {instance.id}"))

        if not options["provision"]:
            return

        plan = plan_runtime(actor, instance)
        provisioning.reserve(actor, instance, plan["fingerprint"])
        receipt = provisioning.execute(instance.id, actor)
        self.stdout.write(self.style.SUCCESS(f"Provisioned runtime, database {receipt.database_id}"))

    def _resolve_organization(self, value):
        try:
            return Organization.objects.get(pk=value)
        except (Organization.DoesNotExist, ValidationError):
            pass
        try:
            return Organization.objects.get(slug=value)
        except Organization.DoesNotExist as exc:
            raise CommandError(f"No such organization: {value}") from exc
