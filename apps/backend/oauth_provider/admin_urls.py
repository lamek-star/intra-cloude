"""Versioned admin API for registering/managing OAuth clients — included
under /api/v1/ from config/api_urls.py, unlike urls.py's protocol
endpoints (see that module's own docstring)."""

from django.urls import path

from . import views

urlpatterns = [
    path("oauth-clients/", views.OAuthClientListCreateView.as_view(), name="oauth-client-list-create"),
    path("oauth-clients/<uuid:client_pk>/", views.OAuthClientDetailView.as_view(), name="oauth-client-detail"),
    path(
        "oauth-clients/<uuid:client_pk>/rotate-secret/",
        views.OAuthClientRotateSecretView.as_view(),
        name="oauth-client-rotate-secret",
    ),
]
