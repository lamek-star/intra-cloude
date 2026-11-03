from django.urls import path, re_path
from django.views.decorators.clickjacking import xframe_options_sameorigin

from . import serve

# Mounted at /_sites/ by config/urls.py. The slug pattern matches services.SLUG_PATTERN's alphabet.
urlpatterns = [
    # A site under its own name; "_host" can never be a site address (addresses have no underscore).
    re_path(r"^_host/(?P<path>.*)$", xframe_options_sameorigin(serve.serve_by_host)),
    re_path(r"^_internet/(?P<path>.*)$", xframe_options_sameorigin(serve.serve_internet)),
    re_path(r"^(?P<slug>[a-z0-9-]{1,50})$", serve.site_root),
    re_path(r"^(?P<slug>[a-z0-9-]{1,50})/(?P<path>.*)$", xframe_options_sameorigin(serve.serve_site)),
    path("", serve.sites_index),
    re_path(r"^(?P<path>.*)$", serve.sites_index),
]
