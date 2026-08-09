from django.urls import path

from . import views

urlpatterns = [
    path(
        "projects/<uuid:project_id>/buckets/",
        views.BucketListCreateView.as_view(),
        name="bucket-list-create",
    ),
    path(
        "buckets/<uuid:bucket_id>/folders/",
        views.FolderListCreateView.as_view(),
        name="folder-list-create",
    ),
    path(
        "buckets/<uuid:bucket_id>/files/",
        views.FileListCreateView.as_view(),
        name="file-list-create",
    ),
    path("files/<uuid:file_id>/", views.FileDetailView.as_view(), name="file-detail"),
    path("files/<uuid:file_id>/download/", views.FileDownloadView.as_view(), name="file-download"),
    path("files/<uuid:file_id>/restore/", views.FileRestoreView.as_view(), name="file-restore"),
    path(
        "files/<uuid:file_id>/versions/",
        views.FileVersionUploadView.as_view(),
        name="file-version-upload",
    ),
]
