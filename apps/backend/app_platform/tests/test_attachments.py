from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import connections
from django.test import TransactionTestCase
from django.urls import reverse
from psycopg import sql
from rest_framework.test import APIClient

from accounts.models import User
from app_platform import instances, provisioning, templates
from app_platform.models import RecordAttachment
from app_platform.runtime_plan import plan_runtime
from app_platform.tests.test_foundation import project_for, sample
from organizations.models import Membership
from organizations.services import create_organization
from permissions.services import grant_resource_permission
from storage.models import FileObject


class AttachmentsTests(TransactionTestCase):
    databases = {"default", "tenant"}

    def setUp(self):
        call_command("seed_permissions", verbosity=0)
        self.actor = User.objects.create_user(email="attach-owner@example.com")
        self.org = create_organization(name="Attach Org", created_by=self.actor)
        self.project = project_for(self.actor, self.org)
        template = templates.create_template(self.actor, self.org, {"label": "App", "draft": sample()})
        version = templates.publish_template(self.actor, template)
        self.instance = instances.install(
            self.actor, self.project, {"label": "Runtime", "template_version": str(version.id)}
        )
        self.plan = plan_runtime(self.actor, self.instance)
        provisioning.reserve(self.actor, self.instance, self.plan["fingerprint"])
        self.receipt = provisioning.execute(self.instance.id, self.actor)

        self.item = self.instance.models.get(key="item")
        self.client = APIClient()
        self.client.force_authenticate(self.actor)

        record = self.client.post(f"/api/v1/app-models/{self.item.id}/records/", {}, format="json")
        self.assertEqual(record.status_code, 201, record.data)
        self.record_id = record.data["id"]

        bucket = self.client.post(
            reverse("bucket-list-create", args=[self.project.id]), {"name": "Attachments"}
        )
        self.assertEqual(bucket.status_code, 201, bucket.data)
        self.bucket_id = bucket.data["id"]

        self.file_id = self._upload("hello.txt", b"hello world")

        self.attachments_url = f"/api/v1/app-models/{self.item.id}/records/{self.record_id}/attachments/"

    def tearDown(self):
        with connections["tenant"].cursor() as cursor:
            cursor.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(self.plan["schema_name"]))
            )
        super().tearDown()

    def _upload(self, name, content, *, content_type="text/plain"):
        upload = SimpleUploadedFile(name, content, content_type=content_type)
        response = self.client.post(
            reverse("file-list-create", args=[self.bucket_id]),
            {"file": upload, "display_filename": name},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data["id"]

    def detail_url(self, attachment_id):
        return f"{self.attachments_url}{attachment_id}/"

    def download_url(self, attachment_id):
        return f"{self.detail_url(attachment_id)}download/"

    def test_attach_list_download_and_detach_round_trip(self):
        attach = self.client.post(self.attachments_url, {"file_id": self.file_id}, format="json")
        self.assertEqual(attach.status_code, 201, attach.data)
        attachment_id = attach.data["id"]
        self.assertEqual(attach.data["filename"], "hello.txt")
        self.assertEqual(attach.data["record_id"], str(self.record_id))

        listing = self.client.get(self.attachments_url)
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.data), 1)
        self.assertEqual(listing.data[0]["id"], attachment_id)
        self.assertNotIn("object_key", listing.data[0])

        download = self.client.get(self.download_url(attachment_id))
        self.assertEqual(download.status_code, 200)
        self.assertEqual(b"".join(download.streaming_content), b"hello world")

        detach = self.client.delete(self.detail_url(attachment_id))
        self.assertEqual(detach.status_code, 204)
        self.assertEqual(self.client.get(self.attachments_url).data, [])
        self.assertFalse(RecordAttachment.objects.filter(pk=attachment_id).exists())

    def test_deleting_the_record_cascades_attachment_rows(self):
        attach = self.client.post(self.attachments_url, {"file_id": self.file_id}, format="json")
        self.assertEqual(attach.status_code, 201, attach.data)

        delete = self.client.delete(f"/api/v1/app-models/{self.item.id}/records/{self.record_id}/")
        self.assertEqual(delete.status_code, 204)
        self.assertFalse(RecordAttachment.objects.filter(model=self.item, record_id=self.record_id).exists())

    def test_quarantined_file_cannot_be_attached(self):
        file_obj = FileObject.objects.get(pk=self.file_id)
        file_obj.status = FileObject.Status.QUARANTINED
        file_obj.save(update_fields=["status"])

        response = self.client.post(self.attachments_url, {"file_id": self.file_id}, format="json")
        self.assertEqual(response.status_code, 400, response.data)

    def test_download_denies_a_file_quarantined_after_attaching(self):
        attach = self.client.post(self.attachments_url, {"file_id": self.file_id}, format="json")
        attachment_id = attach.data["id"]

        file_obj = FileObject.objects.get(pk=self.file_id)
        file_obj.status = FileObject.Status.QUARANTINED
        file_obj.save(update_fields=["status"])

        response = self.client.get(self.download_url(attachment_id))
        self.assertEqual(response.status_code, 403)

    def test_file_from_a_foreign_organization_cannot_be_attached(self):
        outsider = User.objects.create_user(email="attach-outsider@example.com")
        other_org = create_organization(name="Other Attach Org", created_by=outsider)
        Membership.objects.create(user=self.actor, organization=other_org, status=Membership.Status.ACTIVE)
        other_project = project_for(outsider, other_org)

        client = APIClient()
        client.force_authenticate(outsider)
        bucket = client.post(reverse("bucket-list-create", args=[other_project.id]), {"name": "Foreign"})
        self.assertEqual(bucket.status_code, 201, bucket.data)
        upload = SimpleUploadedFile("foreign.txt", b"nope", content_type="text/plain")
        foreign_file = client.post(
            reverse("file-list-create", args=[bucket.data["id"]]),
            {"file": upload, "display_filename": "foreign.txt"},
            format="multipart",
        )
        self.assertEqual(foreign_file.status_code, 201, foreign_file.data)

        # self.actor is a member of both organizations, so a naive
        # membership-only check would let this through.
        response = self.client.post(
            self.attachments_url, {"file_id": foreign_file.data["id"]}, format="json"
        )
        self.assertEqual(response.status_code, 404)

    def test_member_without_storage_read_cannot_attach(self):
        member = User.objects.create_user(email="attach-member@example.com")
        Membership.objects.create(user=member, organization=self.org, status=Membership.Status.ACTIVE)
        grant_resource_permission(
            user=member,
            permission_code="database.write",
            organization_id=self.org.id,
            resource_type="databases.tenant_database",
            resource_id=self.receipt.database_id,
        )
        client = APIClient()
        client.force_authenticate(member)

        response = client.post(self.attachments_url, {"file_id": self.file_id}, format="json")
        self.assertEqual(response.status_code, 403)
