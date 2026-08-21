from django.urls import path

from . import views

urlpatterns = [
    path("tables/<uuid:table_id>/analyze/", views.TableAnalyzeView.as_view(), name="table-analyze"),
    path("tables/<uuid:table_id>/profile/", views.TableProfileView.as_view(), name="table-profile"),
    path(
        "tenant-databases/<uuid:tenant_database_id>/dashboards/",
        views.DashboardListCreateView.as_view(),
        name="dashboard-list-create",
    ),
    path("dashboards/<uuid:dashboard_id>/", views.DashboardDetailView.as_view(), name="dashboard-detail"),
    path(
        "dashboards/<uuid:dashboard_id>/render/",
        views.DashboardRenderView.as_view(),
        name="dashboard-render",
    ),
]
