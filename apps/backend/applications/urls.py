from django.urls import path

from . import views

urlpatterns = [
    path(
        "organizations/<uuid:organization_id>/applications/",
        views.ApplicationListCreateView.as_view(),
        name="application-list-create",
    ),
    path(
        "applications/<uuid:application_id>/",
        views.ApplicationDetailView.as_view(),
        name="application-detail",
    ),
    path(
        "applications/<uuid:application_id>/credentials/",
        views.ApplicationCredentialListCreateView.as_view(),
        name="application-credential-list-create",
    ),
    path(
        "applications/<uuid:application_id>/credentials/<uuid:credential_id>/revoke/",
        views.ApplicationCredentialRevokeView.as_view(),
        name="application-credential-revoke",
    ),
    path(
        "applications/<uuid:application_id>/credentials/<uuid:credential_id>/rotate/",
        views.ApplicationCredentialRotateView.as_view(),
        name="application-credential-rotate",
    ),
    path(
        "applications/<uuid:application_id>/resource-grants/",
        views.ApplicationResourceGrantListCreateView.as_view(),
        name="application-resource-grant-list-create",
    ),
]
