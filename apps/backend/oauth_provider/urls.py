"""
Protocol endpoints — mounted at the application root in config/urls.py
(not under /api/v1/), because /.well-known/openid-configuration's path
is spec-mandated to be exactly that, and the /oauth/* endpoints sit
alongside it by convention rather than inside the versioned resource API.
See infrastructure/proxy/Caddyfile's `@backend` matcher, which must route
these paths to this service too.
"""

from django.urls import path

from . import views

urlpatterns = [
    path("oauth/authorize", views.AuthorizeView.as_view(), name="oauth-authorize"),
    path("oauth/token", views.TokenView.as_view(), name="oauth-token"),
    path("oauth/userinfo", views.UserInfoView.as_view(), name="oauth-userinfo"),
    path("oauth/revoke", views.RevokeView.as_view(), name="oauth-revoke"),
    path("oauth/jwks.json", views.JWKSView.as_view(), name="oauth-jwks"),
    path(".well-known/openid-configuration", views.OpenIDConfigurationView.as_view(), name="oidc-discovery"),
]
