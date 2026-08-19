from django.urls import path

from . import views

urlpatterns = [
    path(
        "organizations/<uuid:organization_id>/export/",
        views.ExportJobListCreateView.as_view(),
        name="export-job-list-create",
    ),
    path("export/<uuid:job_id>/", views.ExportJobDetailView.as_view(), name="export-job-detail"),
    path(
        "export/<uuid:job_id>/download/", views.ExportJobDownloadView.as_view(), name="export-job-download"
    ),
    path("import/", views.RestoreJobListCreateView.as_view(), name="restore-job-list-create"),
    path("import/<uuid:job_id>/", views.RestoreJobDetailView.as_view(), name="restore-job-detail"),
]
