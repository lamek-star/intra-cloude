from django.urls import path

from . import views

urlpatterns = [
    path("files/<uuid:file_id>/import-preview/", views.ImportPreviewView.as_view(), name="import-preview"),
    path(
        "tables/<uuid:table_id>/imports/",
        views.ImportJobListCreateView.as_view(),
        name="import-job-list-create",
    ),
    path("imports/<uuid:job_id>/", views.ImportJobDetailView.as_view(), name="import-job-detail"),
    path(
        "imports/<uuid:job_id>/errors/",
        views.ImportJobErrorListView.as_view(),
        name="import-job-error-list",
    ),
]
