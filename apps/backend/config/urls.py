from django.urls import include, path

urlpatterns = [
    # Liveness/readiness are unauthenticated and unversioned by convention —
    # they're infrastructure endpoints, not part of the public API surface.
    path("", include("system.urls")),
    # OAuth2/OIDC protocol endpoints (/oauth/*, /.well-known/openid-configuration)
    # are unversioned and root-level by spec/convention, exactly like the
    # infrastructure endpoints above — see oauth_provider/urls.py.
    path("", include("oauth_provider.urls")),
    # Versioned API root (Section 14 of the master prompt). Individual
    # module apps mount their own routers here as they're implemented,
    # starting Phase 2 (accounts/organizations/permissions).
    path("api/v1/", include("config.api_urls")),
]
