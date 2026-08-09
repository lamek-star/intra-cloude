import csv
import io

from django.http import Http404, StreamingHttpResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from permissions.services import has_permission
from workspaces.views import get_member_project

from . import rows as row_ops
from . import services
from .models import DBTable
from .serializers import (
    ColumnCreateSerializer,
    ColumnSerializer,
    ForeignKeyCreateSerializer,
    ForeignKeySerializer,
    TableCreateSerializer,
    TableSerializer,
    TenantDatabaseCreateSerializer,
    TenantDatabaseSerializer,
)
from .values import RowValueError


def _request_id(request) -> str:
    return getattr(request, "request_id", "") or ""


def _handle(fn):
    """Runs a schema-service call and maps its exceptions to HTTP
    responses — every view below follows the same shape, so this avoids
    repeating the try/except in each one."""
    try:
        return fn(), None
    except services.SchemaPermissionDenied:
        return None, Response(status=status.HTTP_403_FORBIDDEN)
    except services.SchemaValidationError as exc:
        return None, Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class TenantDatabaseListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        project = get_member_project(request.user, project_id)
        databases = project.tenant_databases.all()
        return Response(TenantDatabaseSerializer(databases, many=True).data)

    def post(self, request, project_id):
        project = get_member_project(request.user, project_id)
        serializer = TenantDatabaseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result, error = _handle(
            lambda: services.create_tenant_database(
                actor=request.user,
                project=project,
                name=serializer.validated_data["name"],
                request_id=_request_id(request),
            )
        )
        if error:
            return error
        return Response(TenantDatabaseSerializer(result).data, status=status.HTTP_201_CREATED)


class TenantDatabaseDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, tenant_database_id):
        tenant_db = services.get_member_tenant_database(request.user, tenant_database_id)
        return Response(TenantDatabaseSerializer(tenant_db).data)

    def delete(self, request, tenant_database_id):
        tenant_db = services.get_member_tenant_database(request.user, tenant_database_id)
        _, error = _handle(
            lambda: services.delete_tenant_database(
                actor=request.user, tenant_database=tenant_db, request_id=_request_id(request)
            )
        )
        if error:
            return error
        return Response(status=status.HTTP_204_NO_CONTENT)


class TableListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, tenant_database_id):
        tenant_db = services.get_member_tenant_database(request.user, tenant_database_id)
        tables = tenant_db.tables.prefetch_related("columns")
        return Response(TableSerializer(tables, many=True).data)

    def post(self, request, tenant_database_id):
        tenant_db = services.get_member_tenant_database(request.user, tenant_database_id)
        serializer = TableCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result, error = _handle(
            lambda: services.create_table(
                actor=request.user,
                tenant_database=tenant_db,
                name=serializer.validated_data["name"],
                request_id=_request_id(request),
            )
        )
        if error:
            return error
        return Response(TableSerializer(result).data, status=status.HTTP_201_CREATED)


class TableDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, table_id):
        table = services.get_member_table(request.user, table_id)
        return Response(TableSerializer(table).data)

    def delete(self, request, table_id):
        table = services.get_member_table(request.user, table_id)
        _, error = _handle(
            lambda: services.delete_table(actor=request.user, table=table, request_id=_request_id(request))
        )
        if error:
            return error
        return Response(status=status.HTTP_204_NO_CONTENT)


class ColumnCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, table_id):
        table = services.get_member_table(request.user, table_id)
        serializer = ColumnCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result, error = _handle(
            lambda: services.add_column(
                actor=request.user,
                table=table,
                name=data["name"],
                data_type=data["data_type"],
                max_length=data["max_length"],
                precision=data["precision"],
                scale=data["scale"],
                is_nullable=data["is_nullable"],
                is_unique=data["is_unique"],
                default_value=data["default_value"],
                request_id=_request_id(request),
            )
        )
        if error:
            return error
        return Response(ColumnSerializer(result).data, status=status.HTTP_201_CREATED)


class ForeignKeyCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, table_id):
        table = services.get_member_table(request.user, table_id)
        serializer = ForeignKeyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        column = services.get_member_column(request.user, data["column_id"])
        if column.table_id != table.id:
            return Response(
                {"detail": "column does not belong to this table"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            references_table = DBTable.objects.get(
                id=data["references_table_id"], tenant_database=table.tenant_database
            )
        except DBTable.DoesNotExist as exc:
            raise Http404 from exc
        references_column = services.get_member_column(request.user, data["references_column_id"])

        result, error = _handle(
            lambda: services.add_foreign_key(
                actor=request.user,
                column=column,
                references_table=references_table,
                references_column=references_column,
                on_delete=data["on_delete"],
                request_id=_request_id(request),
            )
        )
        if error:
            return error
        return Response(ForeignKeySerializer(result).data, status=status.HTTP_201_CREATED)


# --- Data explorer: row-level browse/edit (Section 12 of the master
# prompt) --- server-side pagination/filtering only; never a queryset the
# client could turn into "fetch everything."

_FILTER_PREFIX = "f_"
_RESERVED_QUERY_PARAMS = {"limit", "offset", "ordering", "search"}
# Fine-grained ResourceGrants (Phase 7) for row data are scoped at the
# TenantDatabase level, matching the master prompt's own example scope
# granularity ("database:read" — a database, not an individual table).
RESOURCE_TYPE_TENANT_DATABASE = "databases.tenant_database"


def _database_resource(table: DBTable):
    return (RESOURCE_TYPE_TENANT_DATABASE, table.tenant_database_id)


def _parse_filters(query_params) -> dict:
    return {
        key[len(_FILTER_PREFIX) :]: value
        for key, value in query_params.items()
        if key.startswith(_FILTER_PREFIX)
    }


class RowListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, table_id):
        table = services.get_member_table(request.user, table_id)
        resource = _database_resource(table)
        if not has_permission(
            request.user, "database.read", organization_id=table.organization_id, resource=resource
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            limit = int(request.query_params.get("limit", row_ops.DEFAULT_LIMIT))
            offset = int(request.query_params.get("offset", 0))
        except ValueError:
            return Response({"detail": "limit/offset must be integers"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = row_ops.list_rows(
                table=table,
                limit=limit,
                offset=offset,
                ordering=request.query_params.get("ordering"),
                filters=_parse_filters(request.query_params),
                search=request.query_params.get("search"),
            )
        except RowValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)

    def post(self, request, table_id):
        table = services.get_member_table(request.user, table_id)
        resource = _database_resource(table)
        if not has_permission(
            request.user, "database.write", organization_id=table.organization_id, resource=resource
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        try:
            row = row_ops.insert_row(table, request.data)
        except RowValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(row, status=status.HTTP_201_CREATED)


class RowDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, table_id, row_id):
        table = services.get_member_table(request.user, table_id)
        resource = _database_resource(table)
        if not has_permission(
            request.user, "database.read", organization_id=table.organization_id, resource=resource
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            return Response(row_ops.get_row(table, row_id))
        except row_ops.RowNotFound as exc:
            raise Http404 from exc

    def patch(self, request, table_id, row_id):
        table = services.get_member_table(request.user, table_id)
        resource = _database_resource(table)
        if not has_permission(
            request.user, "database.write", organization_id=table.organization_id, resource=resource
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            return Response(row_ops.update_row(table, row_id, request.data))
        except row_ops.RowNotFound as exc:
            raise Http404 from exc
        except RowValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, table_id, row_id):
        table = services.get_member_table(request.user, table_id)
        resource = _database_resource(table)
        if not has_permission(
            request.user, "database.write", organization_id=table.organization_id, resource=resource
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            row_ops.delete_row(table, row_id)
        except row_ops.RowNotFound as exc:
            raise Http404 from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


class RowExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, table_id):
        table = services.get_member_table(request.user, table_id)
        resource = _database_resource(table)
        if not has_permission(
            request.user, "dataset.export", organization_id=table.organization_id, resource=resource
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)

        def generate():
            for row in row_ops.iter_export_rows(table):
                buf = io.StringIO()
                csv.writer(buf).writerow(row)
                yield buf.getvalue()

        response = StreamingHttpResponse(generate(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{table.name}.csv"'
        return response
