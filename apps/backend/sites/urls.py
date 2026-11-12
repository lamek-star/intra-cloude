from django.urls import path

from . import views

urlpatterns = [
    path("internet-gateway/", views.InternetGatewayView.as_view(), name="internet-gateway"),
    path(
        "internet-gateway/enable/", views.InternetGatewayEnableView.as_view(), name="internet-gateway-enable"
    ),
    path(
        "internet-gateway/disable/",
        views.InternetGatewayDisableView.as_view(),
        name="internet-gateway-disable",
    ),
    path(
        "internet-gateway/auto-publish/",
        views.InternetAutoPublishView.as_view(),
        name="internet-gateway-auto-publish",
    ),
    path("sites/<uuid:site_id>/internet/", views.SiteInternetView.as_view(), name="site-internet"),
    path(
        "organizations/<uuid:organization_id>/sites/",
        views.SiteListCreateView.as_view(),
        name="site-list-create",
    ),
    path("sites/<uuid:site_id>/", views.SiteDetailView.as_view(), name="site-detail"),
    path("sites/<uuid:site_id>/logs/", views.SiteLogsView.as_view(), name="site-logs"),
    path(
        "sites/<uuid:site_id>/versions/",
        views.SiteVersionListCreateView.as_view(),
        name="site-version-list-create",
    ),
    path(
        "sites/<uuid:site_id>/versions/<uuid:version_id>/",
        views.SiteVersionDetailView.as_view(),
        name="site-version-detail",
    ),
    path(
        "sites/<uuid:site_id>/versions/<uuid:version_id>/activate/",
        views.SiteVersionActivateView.as_view(),
        name="site-version-activate",
    ),
]
