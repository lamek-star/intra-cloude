from django.http import Http404, StreamingHttpResponse
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from permissions.services import has_permission
from workspaces.views import get_member_project

from .backends import get_client, safe_content_disposition
from .models import Bucket, FileObject, Folder
from .serializers import (
    BucketCreateSerializer,
    BucketSerializer,
    FileObjectSerializer,
    FileUpdateSerializer,
    FolderCreateSerializer,
    FolderSerializer,
)
from .services import get_member_bucket, get_member_file, upload_file, upload_new_version

# DRF's default JSON parser can't take file uploads; these views also need
# to accept multipart bodies.
_UPLOAD_PARSERS = [MultiPartParser, FormParser]


def _require(request, permission_code, organization_id):
    return has_permission(request.user, permission_code, organization_id=organization_id)


class BucketListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = get_member_project(request.user, project_id)
        buckets = Bucket.objects.filter(project=project)
        return Response(BucketSerializer(buckets, many=True).data)

    def post(self, request, project_id):
        project = get_member_project(request.user, project_id)
        if not _require(request, "storage.manage", project.organization_id):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = BucketCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bucket = Bucket.objects.create(
            project=project,
            name=serializer.validated_data["name"],
            versioning_enabled=serializer.validated_data["versioning_enabled"],
            created_by=request.user,
        )
        return Response(BucketSerializer(bucket).data, status=status.HTTP_201_CREATED)


class FolderListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, bucket_id):
        bucket = get_member_bucket(request.user, bucket_id)
        parent_id = request.query_params.get("parent")
        folders = Folder.objects.filter(bucket=bucket, parent_id=parent_id or None)
        return Response(FolderSerializer(folders, many=True).data)

    def post(self, request, bucket_id):
        bucket = get_member_bucket(request.user, bucket_id)
        if not _require(request, "storage.write", bucket.organization_id):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = FolderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        parent = None
        parent_id = serializer.validated_data["parent_id"]
        if parent_id:
            try:
                parent = Folder.objects.get(id=parent_id, bucket=bucket)
            except Folder.DoesNotExist as exc:
                raise Http404 from exc

        folder = Folder.objects.create(
            bucket=bucket, parent=parent, name=serializer.validated_data["name"], created_by=request.user
        )
        return Response(FolderSerializer(folder).data, status=status.HTTP_201_CREATED)


class FileListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = _UPLOAD_PARSERS

    # Whitelisted to prevent arbitrary-field ordering injection via the
    # query string.
    _ORDERING_FIELDS = {"display_filename", "-display_filename", "created_at", "-created_at", "size", "-size"}

    def get(self, request, bucket_id):
        bucket = get_member_bucket(request.user, bucket_id)
        if not _require(request, "storage.read", bucket.organization_id):
            return Response(status=status.HTTP_403_FORBIDDEN)

        files = FileObject.objects.filter(bucket=bucket, status=FileObject.Status.ACTIVE)

        folder_id = request.query_params.get("folder")
        files = files.filter(folder_id=folder_id or None)

        search = request.query_params.get("search")
        if search:
            files = files.filter(display_filename__icontains=search)

        ordering = request.query_params.get("ordering")
        if ordering in self._ORDERING_FIELDS:
            files = files.order_by(ordering)

        return Response(FileObjectSerializer(files, many=True).data)

    def post(self, request, bucket_id):
        bucket = get_member_bucket(request.user, bucket_id)
        if not _require(request, "storage.write", bucket.organization_id):
            return Response(status=status.HTTP_403_FORBIDDEN)

        uploaded = request.FILES.get("file")
        if uploaded is None:
            return Response({"detail": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

        folder = None
        folder_id = request.data.get("folder")
        if folder_id:
            try:
                folder = Folder.objects.get(id=folder_id, bucket=bucket)
            except Folder.DoesNotExist as exc:
                raise Http404 from exc

        display_filename = request.data.get("display_filename") or uploaded.name
        file_obj = upload_file(
            bucket=bucket,
            folder=folder,
            uploaded_file=uploaded,
            display_filename=display_filename,
            creator=request.user,
        )
        return Response(FileObjectSerializer(file_obj).data, status=status.HTTP_201_CREATED)


class FileDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        file_obj = get_member_file(request.user, file_id)
        if not _require(request, "storage.read", file_obj.organization_id):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(FileObjectSerializer(file_obj).data)

    def patch(self, request, file_id):
        file_obj = get_member_file(request.user, file_id)
        if not _require(request, "storage.write", file_obj.organization_id):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = FileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if "folder" in data:
            if data["folder"] is None:
                file_obj.folder = None
            else:
                try:
                    file_obj.folder = Folder.objects.get(id=data["folder"], bucket=file_obj.bucket)
                except Folder.DoesNotExist as exc:
                    raise Http404 from exc
        if "display_filename" in data:
            file_obj.display_filename = data["display_filename"]
        file_obj.save()
        return Response(FileObjectSerializer(file_obj).data)

    def delete(self, request, file_id):
        file_obj = get_member_file(request.user, file_id)
        if not _require(request, "storage.delete", file_obj.organization_id):
            return Response(status=status.HTTP_403_FORBIDDEN)
        file_obj.status = FileObject.Status.DELETED
        file_obj.save(update_fields=["status", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class FileRestoreView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        file_obj = get_member_file(request.user, file_id)
        if not _require(request, "storage.delete", file_obj.organization_id):
            return Response(status=status.HTTP_403_FORBIDDEN)
        file_obj.status = FileObject.Status.ACTIVE
        file_obj.save(update_fields=["status", "updated_at"])
        return Response(FileObjectSerializer(file_obj).data)


class FileVersionUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = _UPLOAD_PARSERS

    def post(self, request, file_id):
        file_obj = get_member_file(request.user, file_id)
        if not _require(request, "storage.write", file_obj.organization_id):
            return Response(status=status.HTTP_403_FORBIDDEN)

        uploaded = request.FILES.get("file")
        if uploaded is None:
            return Response({"detail": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

        file_obj = upload_new_version(file=file_obj, uploaded_file=uploaded, creator=request.user)
        return Response(FileObjectSerializer(file_obj).data, status=status.HTTP_201_CREATED)


class FileDownloadView(APIView):
    """Streams the file through the backend rather than issuing a
    presigned URL directly to MinIO — OBJECT_STORAGE_ENDPOINT is an
    internal Docker DNS name, unreachable from a browser outside the
    Docker network in this deployment topology. See
    storage/backends.py:ObjectStorageClient.presigned_download_url for
    the alternative, kept working for topologies where it is reachable."""

    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        file_obj = get_member_file(request.user, file_id)
        if not _require(request, "storage.read", file_obj.organization_id):
            return Response(status=status.HTTP_403_FORBIDDEN)

        body = get_client().get_stream(file_obj.object_key)
        response = StreamingHttpResponse(
            body.iter_chunks(1024 * 1024), content_type=file_obj.mime_type
        )
        response["Content-Disposition"] = safe_content_disposition(file_obj.display_filename)
        response["Content-Length"] = str(file_obj.size)
        return response
