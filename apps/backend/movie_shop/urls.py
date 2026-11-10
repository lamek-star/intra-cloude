from django.urls import path

from . import views

urlpatterns = [
    path(
        "organizations/<uuid:organization_id>/movie-shops/",
        views.ShopListCreateView.as_view(),
        name="movie-shop-list",
    ),
    path("movie-shops/<uuid:shop_id>/", views.ShopDetailView.as_view(), name="movie-shop-detail"),
    path("movie-shops/<uuid:shop_id>/prices/", views.ShopPricesView.as_view(), name="movie-shop-prices"),
    path(
        "movie-shops/<uuid:shop_id>/agent-credential/",
        views.AgentCredentialView.as_view(),
        name="movie-shop-agent-credential",
    ),
    path("movie-shops/<uuid:shop_id>/drives/", views.DrivesView.as_view(), name="movie-shop-drives"),
    path(
        "movie-shops/<uuid:shop_id>/libraries/",
        views.LibraryListCreateView.as_view(),
        name="movie-shop-libraries",
    ),
    path(
        "movie-shops/<uuid:shop_id>/categories/",
        views.CategoryListView.as_view(),
        name="movie-shop-categories",
    ),
    path("movie-shops/<uuid:shop_id>/titles/", views.TitleListView.as_view(), name="movie-shop-titles"),
    path(
        "movie-libraries/<uuid:library_id>/", views.LibraryDetailView.as_view(), name="movie-library-detail"
    ),
    path(
        "movie-libraries/<uuid:library_id>/scan/", views.LibraryScanView.as_view(), name="movie-library-scan"
    ),
    path("movie-titles/<uuid:title_id>/", views.TitleDetailView.as_view(), name="movie-title-detail"),
    path("movie-titles/<uuid:title_id>/cover/", views.TitleCoverView.as_view(), name="movie-title-cover"),
    # The media agent (its own credential only)
    path("movie-agent/report/", views.AgentReportView.as_view(), name="movie-agent-report"),
    path(
        "movie-agent/libraries/<uuid:library_id>/scan/start/",
        views.AgentScanStartView.as_view(),
        name="movie-agent-scan-start",
    ),
    path(
        "movie-agent/libraries/<uuid:library_id>/scan/titles/",
        views.AgentScanTitlesView.as_view(),
        name="movie-agent-scan-titles",
    ),
    path(
        "movie-agent/libraries/<uuid:library_id>/scan/finish/",
        views.AgentScanFinishView.as_view(),
        name="movie-agent-scan-finish",
    ),
    path(
        "movie-agent/libraries/<uuid:library_id>/covers/",
        views.AgentCoverView.as_view(),
        name="movie-agent-cover",
    ),
]
