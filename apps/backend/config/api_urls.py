"""
Aggregates each bounded app's `/api/v1/...` routes.
"""

from django.urls import URLPattern, URLResolver, include, path

urlpatterns: list[URLPattern | URLResolver] = [
    path("", include("accounts.urls")),
    path("", include("organizations.urls")),
]
