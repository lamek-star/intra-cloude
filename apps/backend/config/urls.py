from django.urls import include, path

from sites import serve as site_serve

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
    # Hosted websites (ADR-0019). Reached only through the proxy's sites port, which rewrites
    # https://<PC>:8445/<slug>/... to /_sites/<slug>/... and strips cookies; IntraForge's own port
    # answers 404.
    path("_sites/", include("sites.serve_urls")),
    # The proxy's on-demand TLS check for a site's own name (internal network only; never routed from
    # outside).
    path("_sites-certificate/", site_serve.certificate_allowed),
]
