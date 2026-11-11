"""Operator-only, additive upgrade of existing managed runtime schemas."""

from django.core.management.base import BaseCommand
from django.db import transaction

from audit import services as audit

from ...models import RuntimeProvision
from ...operation_journal import install


class Command(BaseCommand):
    help = "Install durable operation journals in existing app runtimes (run before enabling new writers)."

    def handle(self, **options):
        count = 0
        for receipt in RuntimeProvision.objects.filter(
            completed_at__isnull=False, database__isnull=False
        ).select_related("database", "instance"):
            with transaction.atomic(using="tenant"):
                install(receipt.database.schema_name)
            audit.record(
                actor=None, organization_id=receipt.instance.organization_id,
                action="app_instance.runtime.journal.upgrade", resource_type="app_instance",
                resource_id=receipt.instance_id,
            )
            count += 1
        self.stdout.write(f"Operation journals ready in {count} runtimes.")
