import hashlib
import logging
import uuid

from django.conf import settings
from django.db import transaction
from django.http import Http404

from audit import services as audit
from audit.models import AuditEvent
from organizations.models import Membership

from . import scanning
from .backends import get_client, sniff_mime_type
from .models import Bucket, FileObject, FileVersion, Folder

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1024 * 1024  # 1 MiB — files are streamed in chunks this size,
# never read whole into memory (ROADMAP.md Phase 3 exit criteria).


class UploadTooLarge(Exception):
    pass


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
    EOF — callers must `seek(0)` before streaming it onward.

    Aborts as soon as the configured size cap is exceeded rather than
    reading (and hashing) the rest of an oversized upload — no upload
    size limit existed anywhere before this (Section 8 of the master
    prompt: storage must not silently accept arbitrarily large files)."""
    hasher = hashlib.sha256()
    size = 0
    head = b""
    for chunk in iter(lambda: fileobj.read(CHUNK_SIZE), b""):
        if not head:
            head = chunk[:4096]
        hasher.update(chunk)
        size += len(chunk)
        if size > settings.MAX_UPLOAD_SIZE_BYTES:
            raise UploadTooLarge(
                f"file exceeds the maximum upload size of {settings.MAX_UPLOAD_SIZE_BYTES} bytes"
            )
    return hasher.hexdigest(), size, sniff_mime_type(head)


def _scan_for_malware(uploaded_file) -> bool:
    """Returns True only if the file is confirmed clean. A scanner that
    can't be reached is never treated as a clean result — it fails
    closed into quarantine (Section 33 of the master prompt: "do not
    allow a failed scanner to silently mark files clean"). Disabled by
    default (MALWARE_SCAN_ENABLED=False) until an operator has a
    ClamAV daemon reachable at CLAMAV_HOST/CLAMAV_PORT; leaving scanning
    off is a visible, deliberate configuration state, not a silent gap."""
    if not settings.MALWARE_SCAN_ENABLED:
        return True
    uploaded_file.seek(0)
    try:
        result = scanning.scan_stream(uploaded_file)
    except scanning.ScanUnavailable:
        logger.error("Malware scanner unavailable; quarantining upload rather than trusting it clean.")
        return False
    finally:
        uploaded_file.seek(0)
    if not result.clean:
        logger.warning("Malware scan flagged an upload (signature=%s); quarantining.", result.signature)
    return result.clean


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

    is_clean = _scan_for_malware(uploaded_file)
    file_status = FileObject.Status.ACTIVE if is_clean else FileObject.Status.QUARANTINED

    file_id = uuid.uuid4()
    key = _new_object_key(bucket.organization_id, bucket.project_id, bucket.id, file_id)

    client = get_client()
    client.put_stream(key, uploaded_file, mime_type)

    file_obj = FileObject.objects.create(
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
        status=file_status,
    )
    audit.record(
        actor=creator,
        organization_id=bucket.organization_id,
        action="storage.file.upload",
        resource_type="file_object",
        resource_id=file_obj.id,
        result=AuditEvent.Result.SUCCESS if is_clean else AuditEvent.Result.DENIED,
        context={"display_filename": display_filename, "size": size, "quarantined": not is_clean},
    )
    return file_obj


def upload_new_version(*, file: FileObject, uploaded_file, creator) -> FileObject:
    """Overwrites `file`'s content. If its bucket has versioning enabled,
    the previous content's key/checksum/size is preserved in a
    FileVersion row before being replaced; otherwise the old object is
    deleted from storage to avoid leaking space."""
    checksum, size, mime_type = _hash_and_sniff(uploaded_file)
    uploaded_file.seek(0)

    is_clean = _scan_for_malware(uploaded_file)
    new_status = FileObject.Status.ACTIVE if is_clean else FileObject.Status.QUARANTINED

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
        file.status = new_status
        file.save(
            update_fields=["object_key", "size", "checksum_sha256", "mime_type", "status", "updated_at"]
        )

    if not file.bucket.versioning_enabled:
        client.delete(old_key)

    audit.record(
        actor=creator,
        organization_id=file.organization_id,
        action="storage.file.upload_version",
        resource_type="file_object",
        resource_id=file.id,
        result=AuditEvent.Result.SUCCESS if is_clean else AuditEvent.Result.DENIED,
        context={"size": size, "quarantined": not is_clean},
    )
    return file


def delete_file(file: FileObject, *, actor) -> None:
    file.status = FileObject.Status.DELETED
    file.save(update_fields=["status", "updated_at"])
    audit.record(
        actor=actor,
        organization_id=file.organization_id,
        action="storage.file.delete",
        resource_type="file_object",
        resource_id=file.id,
    )


def restore_file(file: FileObject, *, actor) -> None:
    file.status = FileObject.Status.ACTIVE
    file.save(update_fields=["status", "updated_at"])
    audit.record(
        actor=actor,
        organization_id=file.organization_id,
        action="storage.file.restore",
        resource_type="file_object",
        resource_id=file.id,
    )


def record_download(file: FileObject, *, actor) -> None:
    audit.record(
        actor=actor,
        organization_id=file.organization_id,
        action="storage.file.download",
        resource_type="file_object",
        resource_id=file.id,
    )
