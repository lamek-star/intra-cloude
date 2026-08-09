from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from organizations.models import Membership
from permissions.management.commands.seed_permissions import Command as SeedPermissionsCommand
from storage.models import FileVersion

PNG_HEAD = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
TEXT_CONTENT = b"hello world\n" * 1000


def _upload_file(client, url, *, name="hello.txt", content=TEXT_CONTENT, content_type="text/plain", **extra):
    upload = SimpleUploadedFile(name, content, content_type=content_type)
    data = {"file": upload, **extra}
    return client.post(url, data, format="multipart")


class StorageTestBase(APITestCase):
    def setUp(self):
        SeedPermissionsCommand().handle()
        self.admin = User.objects.create_user(email="storage-admin@example.com", password="x")
        self.client.force_login(self.admin)

        org = self.client.post(reverse("organization-list-create"), {"name": "Acme"})
        self.org_id = org.data["id"]

        ws = self.client.post(reverse("workspace-list-create", args=[self.org_id]), {"name": "WS"})
        self.workspace_id = ws.data["id"]

        proj = self.client.post(reverse("project-list-create", args=[self.workspace_id]), {"name": "Proj"})
        self.project_id = proj.data["id"]

        bucket = self.client.post(reverse("bucket-list-create", args=[self.project_id]), {"name": "docs"})
        self.bucket_id = bucket.data["id"]


class BucketFolderTests(StorageTestBase):
    def test_bucket_was_created(self):
        listing = self.client.get(reverse("bucket-list-create", args=[self.project_id]))
        self.assertEqual([b["id"] for b in listing.data], [self.bucket_id])

    def test_create_and_list_folder(self):
        resp = self.client.post(reverse("folder-list-create", args=[self.bucket_id]), {"name": "reports"})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        listing = self.client.get(reverse("folder-list-create", args=[self.bucket_id]))
        self.assertEqual(len(listing.data), 1)
        self.assertEqual(listing.data[0]["name"], "reports")


class FileUploadRoundTripTests(StorageTestBase):
    def test_upload_list_download_delete_restore(self):
        upload_url = reverse("file-list-create", args=[self.bucket_id])
        resp = _upload_file(self.client, upload_url, display_filename="hello.txt")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        file_id = resp.data["id"]
        self.assertEqual(resp.data["size"], len(TEXT_CONTENT))
        self.assertEqual(resp.data["mime_type"], "text/plain")

        listing = self.client.get(upload_url)
        self.assertEqual([f["id"] for f in listing.data], [file_id])

        download = self.client.get(reverse("file-download", args=[file_id]))
        self.assertEqual(download.status_code, status.HTTP_200_OK)
        body = b"".join(download.streaming_content)
        self.assertEqual(body, TEXT_CONTENT)

        delete = self.client.delete(reverse("file-detail", args=[file_id]))
        self.assertEqual(delete.status_code, status.HTTP_204_NO_CONTENT)

        listing_after_delete = self.client.get(upload_url)
        self.assertEqual(listing_after_delete.data, [])

        restore = self.client.post(reverse("file-restore", args=[file_id]))
        self.assertEqual(restore.status_code, status.HTTP_200_OK)
        listing_after_restore = self.client.get(upload_url)
        self.assertEqual([f["id"] for f in listing_after_restore.data], [file_id])

    def test_checksum_is_computed_correctly(self):
        import hashlib

        upload_url = reverse("file-list-create", args=[self.bucket_id])
        resp = _upload_file(self.client, upload_url)
        self.assertEqual(resp.data["checksum_sha256"], hashlib.sha256(TEXT_CONTENT).hexdigest())

    def test_mime_type_is_content_sniffed_not_client_supplied(self):
        upload_url = reverse("file-list-create", args=[self.bucket_id])
        # Client claims text/plain and a .txt name, but the bytes are a PNG
        # signature — the server must not trust either.
        resp = _upload_file(
            self.client,
            upload_url,
            name="not-really.txt",
            content=PNG_HEAD,
            content_type="text/plain",
            display_filename="not-really.txt",
        )
        self.assertEqual(resp.data["mime_type"], "image/png")

    def test_rename_and_move_file(self):
        upload_url = reverse("file-list-create", args=[self.bucket_id])
        uploaded = _upload_file(self.client, upload_url, display_filename="original.txt")
        file_id = uploaded.data["id"]

        folder = self.client.post(reverse("folder-list-create", args=[self.bucket_id]), {"name": "archive"})
        folder_id = folder.data["id"]

        resp = self.client.patch(
            reverse("file-detail", args=[file_id]),
            {"display_filename": "renamed.txt", "folder": folder_id},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["display_filename"], "renamed.txt")
        # response.data holds native Python types pre-JSON-render (a UUID
        # object here, not the string sent in the request) — compare as
        # strings.
        self.assertEqual(str(resp.data["folder"]), str(folder_id))

    def test_search_and_ordering(self):
        upload_url = reverse("file-list-create", args=[self.bucket_id])
        _upload_file(self.client, upload_url, content=b"a", display_filename="alpha.txt")
        _upload_file(self.client, upload_url, content=b"bb", display_filename="beta.txt")

        search = self.client.get(upload_url, {"search": "alpha"})
        self.assertEqual([f["display_filename"] for f in search.data], ["alpha.txt"])

        ordered = self.client.get(upload_url, {"ordering": "-size"})
        self.assertEqual([f["display_filename"] for f in ordered.data], ["beta.txt", "alpha.txt"])

    def test_upload_without_storage_write_permission_is_forbidden(self):
        member = User.objects.create_user(email="plain-member@example.com", password="x")
        Membership.objects.create(user=member, organization_id=self.org_id, status=Membership.Status.ACTIVE)
        self.client.force_login(member)

        resp = _upload_file(self.client, reverse("file-list-create", args=[self.bucket_id]))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class FileVersioningTests(StorageTestBase):
    def test_new_version_creates_history_when_versioning_enabled(self):
        bucket = self.client.post(
            reverse("bucket-list-create", args=[self.project_id]),
            {"name": "versioned", "versioning_enabled": True},
        )
        bucket_id = bucket.data["id"]

        upload_url = reverse("file-list-create", args=[bucket_id])
        first = _upload_file(self.client, upload_url, content=b"v1", display_filename="doc.txt")
        file_id = first.data["id"]
        first_checksum = first.data["checksum_sha256"]

        resp = self.client.post(
            reverse("file-version-upload", args=[file_id]),
            {"file": _make_upload(b"v2", "doc.txt")},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(resp.data["checksum_sha256"], first_checksum)

        versions = FileVersion.objects.filter(file_id=file_id)
        self.assertEqual(versions.count(), 1)
        self.assertEqual(versions.first().checksum_sha256, first_checksum)

    def test_new_version_without_versioning_does_not_keep_history(self):
        upload_url = reverse("file-list-create", args=[self.bucket_id])
        first = _upload_file(self.client, upload_url, content=b"v1", display_filename="doc.txt")
        file_id = first.data["id"]

        self.client.post(
            reverse("file-version-upload", args=[file_id]),
            {"file": _make_upload(b"v2", "doc.txt")},
            format="multipart",
        )
        self.assertEqual(FileVersion.objects.filter(file_id=file_id).count(), 0)


def _make_upload(content, name):
    return SimpleUploadedFile(name, content, content_type="text/plain")
