"""
Per-organization request throttling. DRF's built-in throttle classes key
by user or by IP; several endpoints (import job creation today) instead
need a budget shared across everyone acting within one organization, so
that one compromised or careless member of Org A can't exhaust a shared
resource without touching Org B's separate budget, and so a single
member spinning up many jobs doesn't get a fresh personal allowance
just by switching accounts (docs/security/THREAT_MODEL.md's "per-org job
rate limits/quotas on import/export job creation").
"""

from rest_framework.throttling import SimpleRateThrottle


class OrganizationRateThrottle(SimpleRateThrottle):
    """Keys the throttle cache by (scope, organization_id) rather than by
    user/IP. The view must resolve `request.throttle_organization_id`
    before DRF's `initial()` runs `check_throttles` — see
    `imports/views.py::ImportJobListCreateView.initial` for the pattern.
    If the view never set it (e.g. the resource didn't resolve), this
    throttle simply doesn't apply to that request; the real 404/403
    checks in the view still run as normal afterward.

    `scope`/`rate` aren't known until a request actually arrives (they
    depend on the view), so — exactly like DRF's own ScopedRateThrottle —
    __init__ must NOT call the base class's, which would immediately
    call get_rate() against a still-unset `self.scope` and raise
    ImproperlyConfigured before a single request is even handled."""

    def __init__(self):
        pass

    def allow_request(self, request, view):
        self.scope = getattr(view, "throttle_scope", None)
        organization_id = getattr(request, "throttle_organization_id", None)
        if not self.scope or organization_id is None:
            return True
        self.rate = self.get_rate()
        if self.rate is None:
            return True
        self.num_requests, self.duration = self.parse_rate(self.rate)
        self._organization_id = organization_id
        return super().allow_request(request, view)

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self._organization_id}
