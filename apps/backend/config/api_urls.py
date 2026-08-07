"""
Aggregates each bounded app's `/api/v1/...` routes. Empty at Phase 1 —
apps add an `include("accounts.urls")`-style line here as they gain API
surface, starting with `accounts`/`organizations`/`permissions` in Phase 2.
"""

from django.urls import URLPattern, URLResolver

urlpatterns: list[URLPattern | URLResolver] = []
