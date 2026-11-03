"""
The public side of hosted sites (ADR-0019 decision 4): `/_sites/<slug>/<path>` on the backend, reached only
through the proxy's sites port, which rewrites `https://<PC>:8445/<slug>/...` to it and strips cookies and
credentials. Only paths in the active version's manifest are ever served; the request's user is never
consulted.
"""

from __future__ import annotations

from django.http import HttpResponse, HttpResponseNotAllowed, StreamingHttpResponse

from storage.backends import get_client

from .models import Site

# An opaque origin (no allow-same-origin): the page's scripts run, but cannot read or set cookies, and its
# requests carry no SameSite cookies and Origin: null. This is what keeps a hosted site away from IntraForge's
# sign-in, which shares cookies with every port of the same host.
SANDBOX_POLICY = "sandbox allow-scripts allow-forms allow-popups allow-modals allow-downloads"
_CHUNK = 64 * 1024

_NOT_FOUND_PAGE = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Not found</title>'
    '<meta name="viewport" content="width=device-width, initial-scale=1"></head>'
    '<body style="font-family:system-ui,sans-serif;margin:3rem auto;max-width:32rem;'
    'padding:0 1rem;color:#334">'
    '<h1 style="font-size:1.4rem">This page is not available</h1>'
    "<p>The address may be mistyped, or the website may be offline.</p></body></html>"
)


def _secure(response):
    response["Content-Security-Policy"] = SANDBOX_POLICY
    response["Access-Control-Allow-Origin"] = "*"
    response["X-Content-Type-Options"] = "nosniff"
    response["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response["Cache-Control"] = "no-cache"
    return response


def _app_unavailable():
    page = _NOT_FOUND_PAGE.replace("This page is not available", "This app is starting or stopped").replace(
        "The address may be mistyped, or the website may be offline.",
        "Try again in a minute. If it stays like this, ask the shop to check the app in IntraForge.",
    )
    response = HttpResponse(page, status=503, content_type="text/html; charset=utf-8")
    response["Retry-After"] = "30"
    return _secure(response)


def _not_found():
    return _secure(HttpResponse(_NOT_FOUND_PAGE, status=404, content_type="text/html; charset=utf-8"))


def _file_response(request, version, path: str, entry: dict, status: int = 200):
    etag = f'"{entry["etag"]}"'
    response: HttpResponse | StreamingHttpResponse
    if status == 200 and etag in [t.strip() for t in request.headers.get("If-None-Match", "").split(",")]:
        response = HttpResponse(status=304)
        response["ETag"] = etag
        return _secure(response)
    if request.method == "HEAD":
        response = HttpResponse(status=status, content_type=entry["type"])
    else:
        body = get_client().get_stream(version.storage_prefix + path)
        response = StreamingHttpResponse(body.iter_chunks(_CHUNK), status=status, content_type=entry["type"])
    response["Content-Length"] = str(entry["size"])
    response["ETag"] = etag
    return _secure(response)


def serve_site(request, slug: str, path: str = ""):
    if request.method not in ("GET", "HEAD"):
        return HttpResponseNotAllowed(["GET", "HEAD"])
    site = Site.objects.select_related("active_version").filter(slug=slug, status=Site.Status.ACTIVE).first()
    return _serve(request, site, path, base=f"/{slug}/")


# Set only by the proxy's own-name block (it removes any such header a browser sends first).
SITE_HOST_HEADER = "X-IntraForge-Site-Host"


def serve_by_host(request, path: str = ""):
    """A site under its own name (https://<name>:<sites port>/...): the proxy says which name was
    asked for."""
    if request.method not in ("GET", "HEAD"):
        return HttpResponseNotAllowed(["GET", "HEAD"])
    host = request.headers.get(SITE_HOST_HEADER, "").strip().lower().split(":")[0]
    site = None
    if host:
        site = (
            Site.objects.select_related("active_version")
            .filter(hostname=host, status=Site.Status.ACTIVE)
            .first()
        )
    return _serve(request, site, path, base="/")


def _serve(request, site, path: str, *, base: str):
    if site is None or site.active_version is None:
        return _not_found()
    # A server app is answered by its own container through the proxy (ADR-0020). Reaching this view means
    # it is not running; its files are its source code and are never served from here.
    if site.kind == Site.Kind.NODE or site.active_version.manifest:
        return _app_unavailable()
    version = site.active_version
    files: dict = version.files
    segments = path.split("/")
    if any(s in ("..", ".") for s in segments):
        return _not_found()

    candidate = path + "index.html" if path == "" or path.endswith("/") else path
    entry = files.get(candidate)
    if entry is not None:
        return _file_response(request, version, candidate, entry)
    # A folder named without its trailing slash: send the browser to the folder, so relative links resolve.
    if path and not path.endswith("/") and f"{path}/index.html" in files:
        response = HttpResponse(status=301)
        response["Location"] = f"{base}{path}/"
        return _secure(response)
    if site.single_page_app and "." not in segments[-1] and "index.html" in files:
        return _file_response(request, version, "index.html", files["index.html"])
    if "404.html" in files:
        return _file_response(request, version, "404.html", files["404.html"], status=404)
    return _not_found()


def serve_internet(request, path: str = ""):
    """A site published to the internet, reached through the tunnel and the proxy's internet listener only
    while the gate is on (ADR-0020 decision 4)."""
    if request.method not in ("GET", "HEAD"):
        return HttpResponseNotAllowed(["GET", "HEAD"])
    from .internet import published_site

    host = request.headers.get(SITE_HOST_HEADER, "").strip().lower().split(":")[0]
    return _serve(request, published_site(host), path, base="/")


def certificate_allowed(request):
    """The proxy asks before it issues a certificate for a name (on-demand TLS): only an online site's own
    name gets one. Reached only on the internal network; the proxy never routes this path from outside."""
    name = (request.GET.get("domain") or "").strip().lower()
    allowed = bool(name) and Site.objects.filter(hostname=name, status=Site.Status.ACTIVE).exists()
    return HttpResponse(status=200 if allowed else 404)


def site_root(request, slug: str):
    """`/<slug>` without the slash: relative links in index.html need the slash."""
    response = HttpResponse(status=301)
    response["Location"] = f"/{slug}/"
    return _secure(response)


def sites_index(request, path: str = ""):
    """The bare sites port and anything that is not a site address. No list of sites is given out."""
    return _not_found()
