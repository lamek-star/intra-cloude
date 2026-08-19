from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from databases.models import DBTable
from databases.services import get_member_table
from permissions.services import has_permission
from storage.backends import get_client
from storage.services import get_member_file
from system.throttling import OrganizationRateThrottle

from .inspect import SAMPLE_BYTES, InspectionError, inspect_sample
from .serializers import ImportJobCreateSerializer, ImportJobErrorSerializer, ImportJobSerializer
from .services import (
    ImportPermissionDenied,
    ImportValidationError,
    get_member_import_job,
    start_import,
)


class ImportPreviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        file_obj = get_member_file(request.user, file_id)
        if not has_permission(request.user, "dataset.import", organization_id=file_obj.organization_id):
            return Response(status=status.HTTP_403_FORBIDDEN)

        head = get_client().get_prefix(file_obj.object_key, SAMPLE_BYTES)
        try:
            preview = inspect_sample(head)
        except InspectionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(preview)


class ImportJobListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [OrganizationRateThrottle]
    throttle_scope = "import"

    def initial(self, request, *args, **kwargs):
        # Resolve the owning organization before DRF's check_throttles()
        # runs in the superclass's initial() — OrganizationRateThrottle
        # reads this to key the budget per organization rather than per
        # user. A table_id that doesn't resolve just leaves throttling
        # inapplicable for this request; get_member_table below still
        # enforces the real 404/permission checks either way.
        table_id = kwargs.get("table_id")
        if table_id:
            request.throttle_organization_id = (
                DBTable.objects.filter(id=table_id)
                .values_list("tenant_database__project__workspace__organization_id", flat=True)
                .first()
            )
        super().initial(request, *args, **kwargs)

    def get(self, request, table_id):
        table = get_member_table(request.user, table_id)
        jobs = table.import_jobs.all()
        return Response(ImportJobSerializer(jobs, many=True).data)

    def post(self, request, table_id):
        table = get_member_table(request.user, table_id)
        serializer = ImportJobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        file_obj = get_member_file(request.user, data["file_id"])
        if file_obj.organization_id != table.organization_id:
            return Response(
                {"detail": "file and table must belong to the same organization"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            job = start_import(
                actor=request.user,
                table=table,
                file=file_obj,
                encoding=data["encoding"],
                delimiter=data["delimiter"],
                column_mapping=data["column_mapping"],
            )
        except ImportPermissionDenied:
            return Response(status=status.HTTP_403_FORBIDDEN)
        except ImportValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ImportJobSerializer(job).data, status=status.HTTP_201_CREATED)


class ImportJobDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        job = get_member_import_job(request.user, job_id)
        return Response(ImportJobSerializer(job).data)


class ImportJobErrorListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        job = get_member_import_job(request.user, job_id)
        errors = job.errors.all()[:200]
        return Response(ImportJobErrorSerializer(errors, many=True).data)
