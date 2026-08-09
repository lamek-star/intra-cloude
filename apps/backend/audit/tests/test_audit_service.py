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
