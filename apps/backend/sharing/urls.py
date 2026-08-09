from django.urls import path

from . import views

urlpatterns = [
    path(
        "organizations/<uuid:organization_id>/shares/",
        views.ShareGrantListCreateView.as_view(),
        name="share-grant-list-create",
    ),
    path("shares/<uuid:share_id>/", views.ShareGrantDetailView.as_view(), name="share-grant-detail"),
    path(
        "organizations/<uuid:organization_id>/external-sharing/",
        views.ExternalSharingSettingView.as_view(),
        name="external-sharing-setting",
    ),
]
