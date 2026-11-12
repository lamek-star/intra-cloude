from django.urls import path

from . import views

urlpatterns = [
    path(
        "projects/<uuid:project_id>/buckets/",
        views.BucketListCreateView.as_view(),
        name="bucket-list-create",
    ),
    path(
        "organizations/<uuid:organization_id>/buckets/",
        views.OrganizationBucketListView.as_view(),
        name="organization-bucket-list",
    ),
    path("buckets/<uuid:bucket_id>/", views.BucketDetailView.as_view(), name="bucket-detail"),
    path(
        "files/<uuid:file_id>/share-links/",
        views.FileShareLinkListCreateView.as_view(),
        name="file-share-links",
    ),
    path(
        "share-links/<uuid:link_id>/revoke/",
        views.FileShareLinkRevokeView.as_view(),
        name="share-link-revoke",
    ),
    path("share/<str:token>/", views.PublicShareView.as_view(), name="public-share"),
    path(
        "share/<str:token>/download/",
        views.PublicShareView.as_view(),
        {"download": True},
        name="public-share-download",
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
    path(
        "files/<uuid:file_id>/versions/<uuid:version_id>/download/",
        views.FileVersionDownloadView.as_view(),
        name="file-version-download",
    ),
    path(
        "files/<uuid:file_id>/versions/<uuid:version_id>/restore/",
        views.FileVersionRestoreView.as_view(),
        name="file-version-restore",
    ),
]
