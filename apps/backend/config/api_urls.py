"""
Aggregates each bounded app's `/api/v1/...` routes.
"""

from django.urls import URLPattern, URLResolver, include, path

from system.features import BUSINESS_APPS, FILES_DATA, PAY_MEDIA, WEBSITES_DEVELOPER, gated

urlpatterns: list[URLPattern | URLResolver] = [
    # Feature groups (system/features.py): while a group is switched off its routes answer 403 feature_disabled.
    path("", include(gated(BUSINESS_APPS, "app_platform.urls"))),
    path("", include("accounts.urls")),
    path("", include("organizations.urls")),
    path("", include("org_units.urls")),
    path("", include("workspaces.urls")),
    path("", include(gated(FILES_DATA, "storage.urls"))),
    path("", include(gated(FILES_DATA, "databases.urls"))),
    path("", include("audit.urls")),
    path("", include(gated(FILES_DATA, "imports.urls"))),
    path("", include(gated(WEBSITES_DEVELOPER, "applications.urls"))),
    path("", include(gated(WEBSITES_DEVELOPER, "oauth_provider.admin_urls"))),
    path("", include("catalogue_storage.urls")),
    path("", include(gated(WEBSITES_DEVELOPER, "environments.urls"))),
    path("", include(gated(FILES_DATA, "sharing.urls"))),
    path("", include("exports.urls")),
    path("", include(gated(FILES_DATA, "analytics.urls"))),
    path("", include("service_apps.urls")),
    path("", include(gated(WEBSITES_DEVELOPER, "sites.urls"))),
    path("", include("system.api_urls")),
    path("", include(gated(PAY_MEDIA, "movie_shop.urls"))),
    path("", include("licensing.urls")),
]
