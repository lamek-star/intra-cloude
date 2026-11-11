"""
Hosted websites (ADR-0019): an organization uploads a finished static website as a zip and IntraForge serves
it on its own port. A `SiteVersion` is one uploaded zip, immutable once stored; its files live in object
storage under `sites/<site id>/<version id>/` and `files` is the manifest of exactly what may be served.
"""

import uuid

from django.conf import settings
from django.db import models


class Site(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Online"
        DISABLED = "disabled", "Offline"

    class Kind(models.TextChoices):
        STATIC = "static", "Website"
        NODE = "node", "Node.js app"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="hosted_sites"
    )
    name = models.CharField(max_length=120)
    # The address: https://<PC>:<sites port>/<slug>/. One address space per IntraForge, so globally unique.
    slug = models.SlugField(max_length=50, unique=True)
    # Its own name on the shop network (ADR-0020 decision 3), e.g. "myshop.lan":
    # https://<hostname>:<sites port>/.
    # Never IntraForge's own name or a name under it, so a site cannot set a cookie for IntraForge.
    hostname = models.CharField(max_length=253, unique=True, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    # Client-side routing: an unknown path without a file extension serves the top index.html.
    single_page_app = models.BooleanField(default=False)
    # What the active version is: a static website, or a Node.js app run by the app runner (ADR-0020).
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.STATIC)
    # A server app's identity towards IntraForge: its data, files and Pay are what is granted to this
    # Application (ADR-0020 decision 2). Created on its first deploy.
    application = models.ForeignKey(
        "applications.Application", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    # Published to the internet (ADR-0020 decision 4): its public name (e.g. www.myshop.com), set and
    # revoked only by the Super Administrator while the internet gate is on.
    internet_hostname = models.CharField(max_length=253, unique=True, null=True, blank=True)
    internet_published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    internet_published_at = models.DateTimeField(null=True, blank=True)
    # True when the public name was given by auto-publish (<slug>.<domain>), not typed in by hand: switching
    # auto-publish off, or taking the site offline, takes back only these.
    # db_default: the previous release, run on this data after a failed upgrade rolls back, leaves it out.
    internet_auto = models.BooleanField(default=False, db_default=False)
    # The runner's last answer about a server app ("running", "exited", "failed: ...").
    runtime_state = models.CharField(max_length=40, blank=True)
    runtime_log = models.TextField(blank=True)
    active_version = models.ForeignKey(
        "SiteVersion", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.slug


class SiteVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="versions")
    number = models.PositiveIntegerField()
    original_filename = models.CharField(max_length=255, blank=True)
    # {"<path>": {"size": <bytes>, "type": "<content type>", "etag": "<sha256 prefix>"}}
    files = models.JSONField(default=dict)
    file_count = models.PositiveIntegerField(default=0)
    total_bytes = models.BigIntegerField(default=0)
    # What the upload check left out (hidden files, the removed top folder), shown to the uploader.
    notes = models.JSONField(default=list)
    # A Node.js app's intraforge.json as checked ({"runtime": "node", "entry": ...}); empty for a website.
    manifest = models.JSONField(default=dict, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-number"]
        constraints = [models.UniqueConstraint(fields=["site", "number"], name="site_version_number_unique")]

    def __str__(self) -> str:
        return f"{self.site_id} v{self.number}"

    @property
    def storage_prefix(self) -> str:
        return f"sites/{self.site_id}/{self.id}/"


class InternetGateway(models.Model):
    """The one internet gate of this installation (ADR-0020 decision 4): off unless the Super Administrator
    switches it on. The Cloudflare Tunnel token is kept encrypted and never shown again."""

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    enabled = models.BooleanField(default=False)
    token_encrypted = models.BinaryField(null=True, blank=True)
    # Auto-publish: every online site is published as <slug>.<auto_domain> (a wildcard route in Cloudflare
    # sends those names to the tunnel). Empty: off -- sites are published one by one.
    auto_domain = models.CharField(max_length=200, blank=True, default="", db_default="")
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    changed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return "internet gate: " + ("on" if self.enabled else "off")

    @classmethod
    def current(cls) -> "InternetGateway":
        return cls.objects.get_or_create(pk=1)[0]
