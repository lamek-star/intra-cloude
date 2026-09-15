"""Attach an already-uploaded `storage.FileObject` to a record.

This never uploads or stores bytes itself -- a file must already exist
through the normal storage pipeline (malware scanning, checksum, etc.)
before it can be attached. Attaching only records an association; the
underlying file keeps its own lifecycle (delete/restore/quarantine) and
authorization (`storage.read`/Sharing on its bucket), rechecked here every
time, not just at attach time, per this step's own "downloads must recheck
access and quarantine/deletion state" requirement.
"""

from django.http import Http404

from audit import services as audit
from audit.models import AuditEvent
from permissions.services import has_permission
from storage.models import FileObject
from storage.services import get_member_file, record_download

from . import records
from .models import ModelDefinition, RecordAttachment

RESOURCE_TYPE_BUCKET = "storage.bucket"


class AttachmentAccessDenied(Exception):
    pass


class AttachmentValueError(Exception):
    pass


def _require_storage_read(actor, file_obj: FileObject) -> None:
    allowed = has_permission(
        actor,
        "storage.read",
        organization_id=file_obj.organization_id,
        resource=(RESOURCE_TYPE_BUCKET, file_obj.bucket_id),
    )
    if not allowed:
        raise AttachmentAccessDenied("storage.read required")


def _get_record(model: ModelDefinition, record_id, table) -> None:
    if not records.record_exists(table, record_id):
        raise Http404("Record not found.")


def list_attachments(actor, model: ModelDefinition, record_id):
    _receipt, table = records.resolve(actor, model, "database.read", action="app_instance.attachment.list")
    _get_record(model, record_id, table)
    return RecordAttachment.objects.filter(model=model, record_id=record_id).select_related("file")


def attach_file(actor, model: ModelDefinition, record_id, file_id) -> RecordAttachment:
    _receipt, table = records.resolve(actor, model, "database.write", action="app_instance.attachment.attach")
    _get_record(model, record_id, table)

    file_obj = get_member_file(actor, file_id)
    # `get_member_file` only proves the actor belongs to *a* shared
    # organization with the file -- an actor who is a member of both the
    # app's organization and an unrelated one could otherwise smuggle a
    # foreign organization's file into this record.
    if file_obj.organization_id != model.instance.organization_id:
        raise Http404("File not found.")
    _require_storage_read(actor, file_obj)
    if file_obj.status != FileObject.Status.ACTIVE:
        raise AttachmentValueError("Only an active (not deleted or quarantined) file can be attached.")

    attachment = RecordAttachment.objects.create(
        model=model, record_id=record_id, file=file_obj, created_by=actor
    )
    audit.record(
        actor=actor,
        organization_id=model.instance.organization_id,
        action="app_instance.attachment.attach",
        resource_type="app_model",
        resource_id=model.id,
        context={"record_id": str(record_id), "attachment_id": str(attachment.id), "file_id": str(file_id)},
    )
    return attachment


def detach_attachment(actor, model: ModelDefinition, record_id, attachment_id) -> None:
    records.resolve(actor, model, "database.write", action="app_instance.attachment.detach")
    try:
        attachment = RecordAttachment.objects.get(pk=attachment_id, model=model, record_id=record_id)
    except RecordAttachment.DoesNotExist as exc:
        raise Http404 from exc
    attachment.delete()
    audit.record(
        actor=actor,
        organization_id=model.instance.organization_id,
        action="app_instance.attachment.detach",
        resource_type="app_model",
        resource_id=model.id,
        context={"record_id": str(record_id), "attachment_id": str(attachment_id)},
    )


def prepare_download(actor, model: ModelDefinition, record_id, attachment_id) -> FileObject:
    records.resolve(actor, model, "database.read", action="app_instance.attachment.download")
    try:
        attachment = RecordAttachment.objects.select_related("file__bucket").get(
            pk=attachment_id, model=model, record_id=record_id
        )
    except RecordAttachment.DoesNotExist as exc:
        raise Http404 from exc

    file_obj = attachment.file
    _require_storage_read(actor, file_obj)
    if file_obj.status != FileObject.Status.ACTIVE:
        audit.record(
            actor=actor,
            organization_id=model.instance.organization_id,
            action="app_instance.attachment.download",
            resource_type="app_model",
            resource_id=model.id,
            result=AuditEvent.Result.DENIED,
            context={"record_id": str(record_id), "attachment_id": str(attachment_id)},
        )
        raise AttachmentAccessDenied("This file is no longer available.")

    record_download(file_obj, actor=actor)
    return file_obj
