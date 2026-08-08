from django.core.management.base import BaseCommand
from django.db import transaction

from permissions.catalog import PERMISSIONS, SYSTEM_ROLES
from permissions.models import Permission, Role


class Command(BaseCommand):
    help = "Seeds the Permission catalog and system Roles from permissions.catalog. Idempotent."

    @transaction.atomic
    def handle(self, *args, **options):
        for code, description in PERMISSIONS.items():
            _, created = Permission.objects.update_or_create(
                code=code, defaults={"description": description}
            )
            self.stdout.write(f"{'created' if created else 'ok'} permission: {code}")

        for slug, (name, permission_codes) in SYSTEM_ROLES.items():
            role, created = Role.objects.update_or_create(
                slug=slug,
                organization=None,
                defaults={"name": name, "is_system": True},
            )
            role.permissions.set(Permission.objects.filter(code__in=permission_codes))
            status = "created" if created else "ok"
            self.stdout.write(f"{status} role: {slug} ({len(permission_codes)} permissions)")

        self.stdout.write(self.style.SUCCESS("Permission catalog and system roles seeded."))
