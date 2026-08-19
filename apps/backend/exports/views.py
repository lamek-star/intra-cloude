from django.http import Http404, StreamingHttpResponse
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from organizations.services import get_member_organization

from .models import ExportJob, RestoreJob
from .serializers import ExportJobCreateSerializer, ExportJobSerializer, RestoreJobSerializer
from .services import (
    ExportPermissionDenied,
    RestoreValidationError,
    download_export,
    get_member_export_job,
    stage_restore_upload,
    start_export,
)


class ExportJobListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        org = get_member_organization(request.user, organization_id)
        jobs = ExportJob.objects.filter(organization=org)
        return Response(ExportJobSerializer(jobs, many=True).data)

    def post(self, request, organization_id):
        org = get_member_organization(request.user, organization_id)
        serializer = ExportJobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            job = start_export(
                actor=request.user,
                organization=org,
                passphrase=serializer.validated_data.get("passphrase"),
            )
        except ExportPermissionDenied:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(ExportJobSerializer(job).data, status=status.HTTP_201_CREATED)


class ExportJobDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        job = get_member_export_job(request.user, job_id)
        return Response(ExportJobSerializer(job).data)


class ExportJobDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        job = get_member_export_job(request.user, job_id)
        try:
            body = download_export(actor=request.user, job=job)
        except ExportPermissionDenied:
            return Response(status=status.HTTP_403_FORBIDDEN)
        except RestoreValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        response = StreamingHttpResponse(
            body.iter_chunks(1024 * 1024), content_type="application/octet-stream"
        )
        response["Content-Disposition"] = f'attachment; filename="{job.organization_id}-{job.id}.icp"'
        response["Content-Length"] = str(job.size_bytes)
        return response


class RestoreJobListCreateView(APIView):
    """Deliberately not organization-scoped in its URL — a restore
    creates a brand-new organization, so there is no existing one to
    nest this endpoint under (see services.stage_restore_upload)."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        uploaded = request.FILES.get("package")
        if uploaded is None:
            return Response({"detail": "No package file provided."}, status=status.HTTP_400_BAD_REQUEST)

        passphrase = request.data.get("passphrase") or None
        try:
            job = stage_restore_upload(actor=request.user, uploaded_file=uploaded, passphrase=passphrase)
        except RestoreValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        return Response(RestoreJobSerializer(job).data, status=status.HTTP_201_CREATED)


class RestoreJobDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        try:
            job = RestoreJob.objects.get(id=job_id, created_by=request.user)
        except RestoreJob.DoesNotExist as exc:
            raise Http404 from exc
        return Response(RestoreJobSerializer(job).data)
