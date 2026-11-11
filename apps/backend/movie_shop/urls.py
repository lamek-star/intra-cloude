from django.urls import path

from . import ads_views, portal_views, views

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
    path("movie-shops/<uuid:shop_id>/sales/", views.SaleListCreateView.as_view(), name="movie-shop-sales"),
    path(
        "movie-shops/<uuid:shop_id>/destinations/",
        views.DestinationsView.as_view(),
        name="movie-shop-destinations",
    ),
    path("movie-sales/<uuid:sale_id>/", views.SaleDetailView.as_view(), name="movie-sale-detail"),
    path(
        "movie-sales/<uuid:sale_id>/cash/",
        views.SaleActionView.as_view(action_name="cash"),
        name="movie-sale-cash",
    ),
    path(
        "movie-sales/<uuid:sale_id>/cancel/",
        views.SaleActionView.as_view(action_name="cancel"),
        name="movie-sale-cancel",
    ),
    path(
        "movie-sales/<uuid:sale_id>/retry/",
        views.SaleActionView.as_view(action_name="retry"),
        name="movie-sale-retry",
    ),
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
    path(
        "movie-agent/copies/<uuid:line_id>/", views.AgentCopyProgressView.as_view(), name="movie-agent-copy"
    ),
    path("movie-sales/<uuid:sale_id>/charge/", views.SaleChargeView.as_view(), name="movie-sale-charge"),
    # The customer portal, the owner's side (phase 3)
    path("movie-shops/<uuid:shop_id>/portal/", views.PortalSettingsView.as_view(), name="movie-shop-portal"),
    path(
        "movie-shops/<uuid:shop_id>/customers/", views.CustomerListView.as_view(), name="movie-shop-customers"
    ),
    *[
        path(
            f"movie-customers/<uuid:customer_id>/{name}/",
            views.CustomerActionView.as_view(action_name=name),
            name=f"movie-customer-{name}",
        )
        for name in ("approve", "reject", "block", "unblock", "reset-code", "wallet-password")
    ],
    path(
        "movie-customers/<uuid:customer_id>/points/",
        views.CustomerPointsView.as_view(),
        name="movie-customer-points",
    ),
    # The customer portal itself (no IntraForge sign-in; its own cookie)
    path("portal/<shop_id>/", portal_views.PortalHomeView.as_view(), name="portal-home"),
    path("portal/<shop_id>/signup/", portal_views.PortalSignUpView.as_view(), name="portal-signup"),
    path("portal/<shop_id>/login/", portal_views.PortalSignInView.as_view(), name="portal-login"),
    path("portal/<shop_id>/logout/", portal_views.PortalSignOutView.as_view(), name="portal-logout"),
    path("portal/<shop_id>/me/", portal_views.PortalMeView.as_view(), name="portal-me"),
    path(
        "portal/<shop_id>/categories/", portal_views.PortalCategoriesView.as_view(), name="portal-categories"
    ),
    path("portal/<shop_id>/titles/", portal_views.PortalTitlesView.as_view(), name="portal-titles"),
    path("portal/<shop_id>/titles/<title_id>/", portal_views.PortalTitleView.as_view(), name="portal-title"),
    path(
        "portal/<shop_id>/titles/<title_id>/cover/",
        portal_views.PortalCoverView.as_view(),
        name="portal-cover",
    ),
    path("portal/<shop_id>/orders/", portal_views.PortalOrdersView.as_view(), name="portal-orders"),
    path(
        "portal/<shop_id>/orders/<sale_id>/cancel/",
        portal_views.PortalOrderCancelView.as_view(),
        name="portal-order-cancel",
    ),
    # Ads (phase 4)
    path("movie-shops/<uuid:shop_id>/ads/", ads_views.AdListCreateView.as_view(), name="movie-shop-ads"),
    path("movie-ads/<uuid:ad_id>/", ads_views.AdDetailView.as_view(), name="movie-ad-detail"),
    path("movie-ads/<uuid:ad_id>/picture/", ads_views.AdPictureView.as_view(), name="movie-ad-picture"),
    path("portal/<shop_id>/ads/", ads_views.PortalAdsView.as_view(), name="portal-ads"),
    path(
        "portal/<shop_id>/ads/<ad_id>/picture/",
        ads_views.PortalAdPictureView.as_view(),
        name="portal-ad-picture",
    ),
    path("portal/<shop_id>/ads/<ad_id>/tap/", ads_views.PortalAdTapView.as_view(), name="portal-ad-tap"),
    path(
        "movie-customers/<uuid:customer_id>/",
        views.CustomerDetailView.as_view(),
        name="movie-customer-detail",
    ),
    path("portal/<shop_id>/forgot/", portal_views.PortalForgotView.as_view(), name="portal-forgot"),
    path("portal/<shop_id>/reset/", portal_views.PortalResetView.as_view(), name="portal-reset"),
]
