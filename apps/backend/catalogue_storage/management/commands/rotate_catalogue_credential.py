from django.core.management.base import BaseCommand, CommandError

from applications.models import Application
from applications.services import issue_credential

APPLICATION_NAME = "Harmoney Spare Parts — Catalogue Storage"


class Command(BaseCommand):
    help = (
        "Issues a fresh bearer credential for the seeded "
        f"'{APPLICATION_NAME}' Application and prints it once. "
        "Use when the previous secret was lost, rotated out, or never "
        "correctly captured (e.g. a display bug at seed time)."
    )

    def handle(self, *args, **options):
        try:
            application = Application.objects.get(name=APPLICATION_NAME)
        except Application.DoesNotExist as exc:
            raise CommandError(
                f"No Application named {APPLICATION_NAME!r} exists yet — "
                "run `migrate catalogue_storage` first."
            ) from exc

        credential, token = issue_credential(
            service_account=application.service_account, actor=application.owner
        )
        self.stdout.write(self.style.SUCCESS(f"New credential issued (id={credential.id}):"))
        self.stdout.write(token)
