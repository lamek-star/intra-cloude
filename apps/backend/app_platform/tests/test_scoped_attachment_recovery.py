from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections, transaction
from django.urls import reverse
from rest_framework.test import APIClient

from app_platform import records
from app_platform.runtime_plan import physical_name
from app_platform.tests.test_unit_scope import UnitScopeTestBase
from databases import rows
from permissions.services import grant_resource_permission


class ScopedAttachmentTests(UnitScopeTestBase):
    def test_unit_storage_and_revocation_checks_cover_metadata_and_download(self):
        bucket = self.owner_client.post(
            reverse("bucket-list-create", args=[self.project.pk]), {"name": "Files"}
        )
        self.assertEqual(bucket.status_code, 201)
        upload = self.owner_client.post(
            reverse("file-list-create", args=[bucket.data["id"]]),
            {
                "file": SimpleUploadedFile("invoice-demo.txt", b"DEMO INVOICE"),
                "display_filename": "invoice-demo.txt",
            },
            format="multipart",
        )
        self.assertEqual(upload.status_code, 201)
        urls, ids = [], []
        for record_id in (self.a_record_id, self.b_record_id):
            url = f"{self._detail_url(record_id)}attachments/"
            response = self.owner_client.post(url, {"file_id": upload.data["id"]}, format="json")
            self.assertEqual(response.status_code, 201)
            urls.append(url)
            ids.append(response.data["id"])
        grant = self._grant(self.unit_a.id, "write")
        self.assertEqual(grant.status_code, 201)
        storage_grant = grant_resource_permission(
            user=self.member,
            permission_code="storage.read",
            organization_id=self.org.pk,
            resource_type="storage.bucket",
            resource_id=bucket.data["id"],
        )
        self.assertEqual(len(self.member_client.get(urls[0]).data), 1)
        self.assertEqual(self.member_client.get(urls[1]).status_code, 403)
        self.assertEqual(self.member_client.get(f"{urls[1]}{ids[1]}/download/").status_code, 403)
        self.assertEqual(self.member_client.delete(f"{urls[1]}{ids[1]}/").status_code, 403)
        storage_grant.delete()
        self.assertEqual(self.member_client.get(urls[0]).data, [])
        self.assertEqual(self.member_client.get(f"{urls[0]}{ids[0]}/download/").status_code, 403)
        self.owner_client.delete(f"/api/v1/app-unit-grants/{grant.data['id']}/")
        self.assertEqual(self.member_client.get(urls[0]).status_code, 403)


class UnitMutationRaceTests(UnitScopeTestBase):
    def test_unit_reassignment_while_writer_waits_is_checked_after_row_lock(self):
        self.assertEqual(self._grant(self.unit_a.id, "write").status_code, 201)
        table = records._table(self.receipt, self.task)
        reached_lock = Event()
        original = records.lock_record

        def observed_lock(*args, **kwargs):
            reached_lock.set()
            return original(*args, **kwargs)

        def write_as_member():
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(self.member)
                return client.patch(
                    self._detail_url(self.a_record_id),
                    {str(self.name_field.pk): "Unauthorized change"},
                    format="json",
                ).status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic(using="tenant"):
                rows.update_row(
                    table,
                    self.a_record_id,
                    {
                        physical_name("f", str(self.unit_field.pk)): str(self.unit_b.pk),
                    },
                )
                with patch("app_platform.records.lock_record", side_effect=observed_lock):
                    future = pool.submit(write_as_member)
                    self.assertTrue(reached_lock.wait(10))
            self.assertEqual(future.result(timeout=10), 403)
        row = records.get_record(self.owner, self.task, self.a_record_id)
        self.assertEqual(row[str(self.name_field.pk)], "Task")
