"""Attachment endpoints; see attachments.py for authorization/validation."""

from django.http import StreamingHttpResponse
from rest_framework import serializers
from rest_framework.response import Response

from storage.backends import get_client, safe_content_disposition

from . import attachments
from .access import get_owned
from .definitions import StrictSerializer
from .models import ModelDefinition
from .views import FoundationView


class AttachInput(StrictSerializer):
    file_id = serializers.UUIDField()


def _get_model(request, object_id):
    return get_owned(ModelDefinition, object_id, request.user, "instance__organization")


def _serialize(attachment) -> dict:
    file_obj = attachment.file
    return {
        "id": str(attachment.id),
        "record_id": str(attachment.record_id),
        "file_id": str(file_obj.id),
        "filename": file_obj.display_filename,
        "mime_type": file_obj.mime_type,
        "size": file_obj.size,
        "status": file_obj.status,
        "created_at": attachment.created_at,
    }


class AttachmentListCreateView(FoundationView):
    service_account_methods = frozenset({"GET", "POST"})

    def get(self, request, object_id, record_id):
        model = _get_model(request, object_id)
        try:
            rows = attachments.list_attachments(request.user, model, record_id)
        except attachments.AttachmentAccessDenied:
            return Response(status=403)
        return Response([_serialize(row) for row in rows])

    def post(self, request, object_id, record_id):
        model = _get_model(request, object_id)
        serializer = AttachInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            attachment = attachments.attach_file(
                request.user, model, record_id, serializer.validated_data["file_id"]
            )
        except attachments.AttachmentAccessDenied:
            return Response(status=403)
        except attachments.AttachmentValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(_serialize(attachment), status=201)


class AttachmentDetailView(FoundationView):
    service_account_methods = frozenset({"DELETE"})

    def delete(self, request, object_id, record_id, attachment_id):
        model = _get_model(request, object_id)
        try:
            attachments.detach_attachment(request.user, model, record_id, attachment_id)
        except attachments.AttachmentAccessDenied:
            return Response(status=403)
        return Response(status=204)


class AttachmentDownloadView(FoundationView):
    service_account_methods = frozenset({"GET"})

    def get(self, request, object_id, record_id, attachment_id):
        model = _get_model(request, object_id)
        try:
            file_obj = attachments.prepare_download(request.user, model, record_id, attachment_id)
        except attachments.AttachmentAccessDenied as exc:
            return Response({"detail": str(exc)}, status=403)

        body = get_client().get_stream(file_obj.object_key)
        response = StreamingHttpResponse(body.iter_chunks(1024 * 1024), content_type=file_obj.mime_type)
        response["Content-Disposition"] = safe_content_disposition(file_obj.display_filename)
        response["Content-Length"] = str(file_obj.size)
        return response
