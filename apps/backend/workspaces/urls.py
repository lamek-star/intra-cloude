from django.urls import path

from . import views

urlpatterns = [
    path(
        "organizations/<uuid:organization_id>/workspaces/",
        views.WorkspaceListCreateView.as_view(),
        name="workspace-list-create",
    ),
    path("workspaces/<uuid:workspace_id>/", views.WorkspaceDetailView.as_view(), name="workspace-detail"),
    path(
        "workspaces/<uuid:workspace_id>/projects/",
        views.ProjectListCreateView.as_view(),
        name="project-list-create",
    ),
    path("projects/<uuid:project_id>/", views.ProjectDetailView.as_view(), name="project-detail"),
]
