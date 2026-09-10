"""Native many-to-many relationships for App Platform. Built up
incrementally alongside the feature -- this first slice covers only the
data-model change (RelationshipDefinition.kind now allows "many_to_many",
deletion_policy normalization); provisioning/record-level tests land in
later commits as the corresponding code ships (see
C:\\Users\\Hp\\.claude\\plans\\precious-inventing-seal.md for the full
sequencing)."""

from django.core.management import call_command
from django.db import transaction
from django.test import TestCase

from accounts.models import User
from app_platform import instances, templates
from app_platform.models import RelationshipDefinition
from app_platform.tests.test_foundation import project_for, sample
from organizations.services import create_organization


class RelationshipKindTests(TestCase):
    """Pre-provision only -- no tenant DB involved yet, matching
    instances.add_relationship's existing behavior for an unprovisioned
    instance (a pure metadata write)."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_permissions", verbosity=0)
        cls.owner = User.objects.create_user(email="m2m-owner@example.com")
        cls.org = create_organization(name="M2M Org", created_by=cls.owner)
        cls.project = project_for(cls.owner, cls.org)
        template = templates.create_template(cls.owner, cls.org, {"label": "App", "draft": sample()})
        version = templates.publish_template(cls.owner, template)
        cls.instance = instances.install(
            cls.owner, cls.project, {"label": "Runtime", "template_version": str(version.id)}
        )
        cls.item = cls.instance.models.get(key="item")
        cls.group = cls.instance.models.get(key="group")

    def test_many_to_many_kind_is_accepted_and_persisted(self):
        relation = instances.add_relationship(
            self.owner,
            self.instance,
            {
                "key": "compatible_groups",
                "label": "Compatible Groups",
                "source_model": str(self.item.id),
                "target_model": str(self.group.id),
                "kind": "many_to_many",
            },
        )
        self.assertEqual(relation.kind, "many_to_many")
        relation.refresh_from_db()
        self.assertEqual(relation.kind, "many_to_many")

    def test_deletion_policy_is_normalized_to_restrict_for_many_to_many(self):
        relation = instances.add_relationship(
            self.owner,
            self.instance,
            {
                "key": "compatible_groups_2",
                "label": "Compatible Groups 2",
                "source_model": str(self.item.id),
                "target_model": str(self.group.id),
                "kind": "many_to_many",
                "deletion_policy": "set_null",
            },
        )
        self.assertEqual(relation.deletion_policy, "restrict")

    def test_many_to_one_kind_still_works_unchanged(self):
        relation = instances.add_relationship(
            self.owner,
            self.instance,
            {
                "key": "backup_group",
                "label": "Backup Group",
                "source_model": str(self.item.id),
                "target_model": str(self.group.id),
            },
        )
        self.assertEqual(relation.kind, "many_to_one")

    def test_database_constraint_still_rejects_an_invalid_kind_value(self):
        """The CheckConstraint genuinely narrows to exactly these two
        values, not left wide open -- a raw write bypassing the
        serializer entirely must still be rejected at the DB layer,
        matching this project's own "database constraint is the real
        gate" discipline."""
        relation = RelationshipDefinition(
            instance=self.instance,
            key="invalid_kind_probe",
            label="Invalid",
            source_model=self.item,
            target_model=self.group,
            kind="one_to_one",
            position=999,
        )
        # A nested atomic block gives Postgres a savepoint to roll back to
        # on failure -- without it, the failed INSERT poisons the whole
        # test-wrapping transaction and every later query in this test
        # (and, since setUpTestData's transaction wraps the class, every
        # later test in this class) raises "current transaction is
        # aborted" instead.
        with self.assertRaises(Exception) as ctx:
            with transaction.atomic():
                relation.save()
        self.assertIn("app_relation_kind_valid", str(ctx.exception))
