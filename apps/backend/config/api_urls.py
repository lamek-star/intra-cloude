"""
Aggregates each bounded app's `/api/v1/...` routes.
"""

from django.urls import URLPattern, URLResolver, include, path

urlpatterns: list[URLPattern | URLResolver] = [
    path("", include("accounts.urls")),
    path("", include("organizations.urls")),
    path("", include("workspaces.urls")),
    path("", include("storage.urls")),
    path("", include("databases.urls")),
    path("", include("audit.urls")),
    path("", include("imports.urls")),
    path("", include("applications.urls")),
    path("", include("sharing.urls")),
    path("", include("exports.urls")),
    path("", include("analytics.urls")),
]
