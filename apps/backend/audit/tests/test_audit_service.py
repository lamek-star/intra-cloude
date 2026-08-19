from django.test import TestCase

from accounts.models import User
from audit.models import AuditEvent
from audit.services import record
from organizations.models import Organization


class RecordTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="audit-unit@example.com", password="x")
        self.org = Organization.objects.create(name="Org", slug="org", created_by=self.user)

    def test_record_creates_an_event(self):
        event = record(
            actor=self.user,
            organization_id=self.org.id,
            action="storage.file.delete",
            resource_type="file_object",
            resource_id="some-id",
        )
        self.assertEqual(AuditEvent.objects.count(), 1)
        self.assertEqual(event.result, AuditEvent.Result.SUCCESS)
        self.assertEqual(event.actor, self.user)

    def test_record_with_unauthenticated_actor_stores_no_actor(self):
        from django.contrib.auth.models import AnonymousUser

        event = record(
            actor=AnonymousUser(),
            organization_id=self.org.id,
            action="auth.login",
            result=AuditEvent.Result.DENIED,
        )
        self.assertIsNone(event.actor)


class ImmutabilityTests(TestCase):
    """Section 40: audit records must be protected from ordinary user
    modification. Both the single-instance path (event.save()) and the
    bulk queryset path (AuditEvent.objects.filter(...).delete(), which
    never calls an instance's delete() method) must be blocked."""

    def setUp(self):
        self.user = User.objects.create_user(email="audit-immutable@example.com", password="x")
        self.org = Organization.objects.create(name="Org", slug="org2", created_by=self.user)
        self.event = record(actor=self.user, organization_id=self.org.id, action="organization.create")

    def test_modifying_an_existing_event_is_rejected(self):
        self.event.action = "tampered"
        with self.assertRaises(ValueError):
            self.event.save()

    def test_instance_delete_is_rejected(self):
        with self.assertRaises(ValueError):
            self.event.delete()

    def test_bulk_queryset_delete_is_rejected(self):
        from django.db import transaction

        # The failed delete needs its own savepoint — without it, the
        # ValueError raised mid-transaction leaves the outer test
        # transaction unusable for the assertion query right after.
        with self.assertRaises(ValueError), transaction.atomic():
            AuditEvent.objects.filter(id=self.event.id).delete()
        self.assertTrue(AuditEvent.objects.filter(id=self.event.id).exists())
