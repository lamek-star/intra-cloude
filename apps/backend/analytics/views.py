from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from databases.services import get_member_table, get_member_tenant_database

from .data import AnalyticsValidationError
from .models import Dashboard
from .serializers import (
    AnalysisRequestSerializer,
    DashboardCreateSerializer,
    DashboardSerializer,
    DashboardUpdateSerializer,
)
from .services import (
    AnalyticsPermissionDenied,
    create_dashboard,
    delete_dashboard,
    get_member_dashboard,
    render_dashboard,
    run_analysis,
    run_profile,
    update_dashboard,
)


class TableAnalyzeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, table_id):
        table = get_member_table(request.user, table_id)
        serializer = AnalysisRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = run_analysis(
                actor=request.user,
                table=table,
                operation=serializer.validated_data["operation"],
                params=serializer.validated_data["params"],
            )
        except AnalyticsPermissionDenied:
            return Response(status=status.HTTP_403_FORBIDDEN)
        except AnalyticsValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class TableProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, table_id):
        table = get_member_table(request.user, table_id)
        try:
            result = run_profile(actor=request.user, table=table)
        except AnalyticsPermissionDenied:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(result)


class DashboardListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, tenant_database_id):
        tenant_db = get_member_tenant_database(request.user, tenant_database_id)
        dashboards = Dashboard.objects.filter(tenant_database=tenant_db)
        return Response(DashboardSerializer(dashboards, many=True).data)

    def post(self, request, tenant_database_id):
        tenant_db = get_member_tenant_database(request.user, tenant_database_id)
        serializer = DashboardCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            dashboard = create_dashboard(
                actor=request.user,
                tenant_database=tenant_db,
                name=serializer.validated_data["name"],
                widgets=serializer.validated_data["widgets"],
            )
        except AnalyticsPermissionDenied:
            return Response(status=status.HTTP_403_FORBIDDEN)
        except AnalyticsValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DashboardSerializer(dashboard).data, status=status.HTTP_201_CREATED)


class DashboardDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, dashboard_id):
        dashboard = get_member_dashboard(request.user, dashboard_id)
        return Response(DashboardSerializer(dashboard).data)

    def patch(self, request, dashboard_id):
        dashboard = get_member_dashboard(request.user, dashboard_id)
        serializer = DashboardUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            dashboard = update_dashboard(
                actor=request.user,
                dashboard=dashboard,
                name=serializer.validated_data.get("name"),
                widgets=serializer.validated_data.get("widgets"),
            )
        except AnalyticsPermissionDenied:
            return Response(status=status.HTTP_403_FORBIDDEN)
        except AnalyticsValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DashboardSerializer(dashboard).data)

    def delete(self, request, dashboard_id):
        dashboard = get_member_dashboard(request.user, dashboard_id)
        try:
            delete_dashboard(actor=request.user, dashboard=dashboard)
        except AnalyticsPermissionDenied:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DashboardRenderView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, dashboard_id):
        dashboard = get_member_dashboard(request.user, dashboard_id)
        return Response(render_dashboard(actor=request.user, dashboard=dashboard))
