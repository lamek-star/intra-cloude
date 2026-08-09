import hashlib
import uuid

from django.db import transaction
from django.http import Http404

from organizations.models import Membership

from .backends import get_client, sniff_mime_type
from .models import Bucket, FileObject, FileVersion, Folder

CHUNK_SIZE = 1024 * 1024  # 1 MiB — files are streamed in chunks this size,
# never read whole into memory (ROADMAP.md Phase 3 exit criteria).


def get_member_bucket(user, bucket_id) -> Bucket:
    try:
        return Bucket.objects.select_related("project__workspace__organization").get(
            id=bucket_id,
            project__workspace__organization__memberships__user=user,
            project__workspace__organization__memberships__status=Membership.Status.ACTIVE,
        )
    except Bucket.DoesNotExist as exc:
        raise Http404 from exc


def get_member_file(user, file_id) -> FileObject:
    try:
        return FileObject.objects.select_related("bucket__project__workspace__organization").get(
            id=file_id,
            bucket__project__workspace__organization__memberships__user=user,
            bucket__project__workspace__organization__memberships__status=Membership.Status.ACTIVE,
        )
    except FileObject.DoesNotExist as exc:
        raise Http404 from exc


def _hash_and_sniff(fileobj) -> tuple[str, int, str]:
    """Single chunked pass over the uploaded file: computes its SHA-256
    checksum and sniffs its MIME type from the first chunk, without ever
    holding the whole file in memory. Leaves `fileobj` positioned at
    EOF — callers must `seek(0)` before streaming it onward."""
    hasher = hashlib.sha256()
    size = 0
    head = b""
    for chunk in iter(lambda: fileobj.read(CHUNK_SIZE), b""):
        if not head:
            head = chunk[:4096]
        hasher.update(chunk)
        size += len(chunk)
    return hasher.hexdigest(), size, sniff_mime_type(head)


def _new_object_key(organization_id, project_id, bucket_id, file_id) -> str:
    # Server-generated, no user input anywhere in the key — prevents path
    # traversal / collision (Section 8 of the master prompt). A fresh
    # UUID per physical upload means overwrites never reuse a key.
    return f"{organization_id}/{project_id}/{bucket_id}/{file_id}/{uuid.uuid4()}"


def upload_file(
    *, bucket: Bucket, folder: Folder | None, uploaded_file, display_filename: str, creator
) -> FileObject:
    checksum, size, mime_type = _hash_and_sniff(uploaded_file)
    uploaded_file.seek(0)

    file_id = uuid.uuid4()
    key = _new_object_key(bucket.organization_id, bucket.project_id, bucket.id, file_id)

    client = get_client()
    client.put_stream(key, uploaded_file, mime_type)

    return FileObject.objects.create(
        id=file_id,
        bucket=bucket,
        folder=folder,
        object_key=key,
        original_filename=uploaded_file.name,
        display_filename=display_filename,
        mime_type=mime_type,
        size=size,
        checksum_sha256=checksum,
        creator=creator,
    )


def upload_new_version(*, file: FileObject, uploaded_file, creator) -> FileObject:
    """Overwrites `file`'s content. If its bucket has versioning enabled,
    the previous content's key/checksum/size is preserved in a
    FileVersion row before being replaced; otherwise the old object is
    deleted from storage to avoid leaking space."""
    checksum, size, mime_type = _hash_and_sniff(uploaded_file)
    uploaded_file.seek(0)

    new_key = _new_object_key(file.organization_id, file.bucket.project_id, file.bucket_id, file.id)
    client = get_client()
    client.put_stream(new_key, uploaded_file, mime_type)

    old_key = file.object_key
    with transaction.atomic():
        if file.bucket.versioning_enabled:
            FileVersion.objects.create(
                file=file,
                object_key=old_key,
                size=file.size,
                checksum_sha256=file.checksum_sha256,
                created_by=creator,
            )
        file.object_key = new_key
        file.size = size
        file.checksum_sha256 = checksum
        file.mime_type = mime_type
        file.save(update_fields=["object_key", "size", "checksum_sha256", "mime_type", "updated_at"])

    if not file.bucket.versioning_enabled:
        client.delete(old_key)

    return file


def delete_file(file: FileObject) -> None:
    file.status = FileObject.Status.DELETED
    file.save(update_fields=["status", "updated_at"])


def restore_file(file: FileObject) -> None:
    file.status = FileObject.Status.ACTIVE
    file.save(update_fields=["status", "updated_at"])
