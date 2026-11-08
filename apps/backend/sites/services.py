"""
Hosted-site lifecycle (ADR-0019): create a site from a zip, upload further versions, switch the active
version, take a site offline, delete versions and sites. Every change records an audit event. Files are
written to object storage before the version row exists and removed again if anything fails, so a version
row always has its files.
"""

from __future__ import annotations

import hashlib
import re
import uuid

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Max

from applications.models import ApplicationCredential
from applications.services import issue_credential, register_application, revoke_credential
from audit import services as audit
from audit.models import AuditEvent
from storage.backends import get_client

from . import runner
from .archive import SiteArchiveError, plan_archive
from .models import Site, SiteVersion

SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,48}[a-z0-9])?$")
# Addresses the sites port itself might need, or that would only confuse visitors.
RESERVED_SLUGS = {"_sites", "api", "apps", "static", "assets", "admin", "www", "sites", "intraforge"}


class SiteError(ValueError):
    pass


class _HashingReader:
    """Wraps a zip entry so the bytes are hashed while boto3 streams them to object storage."""

    def __init__(self, raw):
        self._raw = raw
        self.digest = hashlib.sha256()

    def read(self, size=-1):
        chunk = self._raw.read(size)
        self.digest.update(chunk)
        return chunk


def validate_slug(slug: str) -> str:
    slug = (slug or "").strip().lower()
    if not SLUG_PATTERN.match(slug):
        raise SiteError(
            "The address may use lower-case letters, digits and hyphens (up to 50), "
            "and must start and end with a letter or digit."
        )
    if slug in RESERVED_SLUGS:
        raise SiteError(f"'{slug}' is reserved; choose another address.")
    return slug


def _store_version(*, site: Site, upload, actor) -> SiteVersion:
    if upload.size > settings.SITES_MAX_ZIP_BYTES:
        raise SiteError(f"The zip is larger than {settings.SITES_MAX_ZIP_BYTES // (1024 * 1024)} MB.")
    try:
        archive, plan = plan_archive(upload)
    except SiteArchiveError as exc:
        raise SiteError(str(exc)) from exc
    if plan.manifest and not runner.configured():
        archive.close()
        raise SiteError("This zip is a Node.js app, and server apps are not available on this installation.")

    version_id = uuid.uuid4()
    prefix = f"sites/{site.id}/{version_id}/"
    client = get_client()
    stored: list[str] = []
    manifest: dict[str, dict] = {}
    try:
        with archive:
            for planned in plan.files:
                key = prefix + planned.path
                with archive.open(planned.entry) as raw:
                    reader = _HashingReader(raw)
                    client.put_stream(key, reader, planned.content_type)
                stored.append(key)
                manifest[planned.path] = {
                    "size": planned.size,
                    "type": planned.content_type,
                    "etag": reader.digest.hexdigest()[:32],
                }
        with transaction.atomic():
            # Lock the site so two uploads at once cannot take the same version number.
            Site.objects.select_for_update().get(pk=site.pk)
            number = (site.versions.aggregate(n=Max("number"))["n"] or 0) + 1
            version = SiteVersion.objects.create(
                id=version_id,
                site=site,
                number=number,
                original_filename=(getattr(upload, "name", "") or "")[:255],
                files=manifest,
                file_count=len(manifest),
                total_bytes=plan.total_bytes,
                notes=plan.notes,
                manifest=plan.manifest or {},
                uploaded_by=actor,
            )
    except Exception:
        for key in stored:
            client.delete(key)
        raise
    return version


def create_site(*, organization, name: str, slug: str, upload, actor, single_page_app: bool = False) -> Site:
    name = (name or "").strip()
    if not name:
        raise SiteError("Give the site a name.")
    slug = validate_slug(slug)
    if Site.objects.filter(slug=slug).exists():
        raise SiteError(f"The address '{slug}' is already in use; choose another.")
    try:
        with transaction.atomic():
            site = Site.objects.create(
                organization=organization,
                name=name[:120],
                slug=slug,
                single_page_app=single_page_app,
                created_by=actor,
            )
    except IntegrityError as exc:
        raise SiteError(f"The address '{slug}' is already in use; choose another.") from exc
    try:
        version = _store_version(site=site, upload=upload, actor=actor)
    except Exception:
        site.delete()
        raise
    site.active_version = version
    site.save(update_fields=["active_version", "updated_at"])
    audit.record(
        actor=actor,
        organization_id=organization.id,
        action="site.created",
        resource_type="site",
        resource_id=site.id,
        context={"slug": slug, "name": site.name, "version": version.number, "files": version.file_count},
    )
    _apply_version(site, version, actor)
    _internet_follow(site)
    return site


def _internet_follow(site: Site) -> None:
    """Auto-publish follows the site: online, it gets its automatic public name; offline, it gives it back."""
    from . import internet  # internet.py imports this module

    if site.status == Site.Status.ACTIVE:
        internet.auto_publish(site)
    else:
        internet.withdraw_auto(site)


def upload_version(*, site: Site, upload, actor, activate: bool = True) -> SiteVersion:
    version = _store_version(site=site, upload=upload, actor=actor)
    audit.record(
        actor=actor,
        organization_id=site.organization_id,
        action="site.version.uploaded",
        resource_type="site",
        resource_id=site.id,
        context={"slug": site.slug, "version": version.number, "files": version.file_count},
    )
    if activate:
        activate_version(site=site, version=version, actor=actor)
    return version


def activate_version(*, site: Site, version: SiteVersion, actor) -> Site:
    if version.site_id != site.id:
        raise SiteError("That version belongs to another site.")
    previous = site.active_version.number if site.active_version else None
    site.active_version = version
    site.save(update_fields=["active_version", "updated_at"])
    audit.record(
        actor=actor,
        organization_id=site.organization_id,
        action="site.version.activated",
        resource_type="site",
        resource_id=site.id,
        context={"slug": site.slug, "version": version.number, "previous_version": previous},
    )
    _apply_version(site, version, actor)
    return site


def update_site(*, site: Site, actor, **fields) -> Site:
    changed = {}
    if "name" in fields:
        name = (fields["name"] or "").strip()
        if not name:
            raise SiteError("Give the site a name.")
        changed["name"] = name[:120]
    if "status" in fields:
        if fields["status"] not in Site.Status.values:
            raise SiteError("Status is 'active' or 'disabled'.")
        changed["status"] = fields["status"]
    if "single_page_app" in fields:
        changed["single_page_app"] = bool(fields["single_page_app"])
    if site.kind == Site.Kind.NODE and changed.get("status", site.status) != site.status:
        try:
            result = runner.start(site) if changed["status"] == Site.Status.ACTIVE else runner.stop(site)
        except (runner.RunnerUnavailable, runner.RunnerRefused) as exc:
            raise SiteError(str(exc)) from exc
        _record_runtime(site, result)
    for key, value in changed.items():
        setattr(site, key, value)
    if changed:
        site.save(update_fields=[*changed, "updated_at"])
        audit.record(
            actor=actor,
            organization_id=site.organization_id,
            action="site.updated",
            resource_type="site",
            resource_id=site.id,
            context={"slug": site.slug, **changed},
        )
        if "status" in changed:
            _internet_follow(site)
    return site


def _delete_files(version: SiteVersion) -> None:
    client = get_client()
    for path in version.files:
        client.delete(version.storage_prefix + path)


def delete_version(*, site: Site, version: SiteVersion, actor) -> None:
    if site.active_version_id == version.id:
        raise SiteError("This version is the one visitors see. Switch to another version before deleting it.")
    number = version.number
    _delete_files(version)
    version.delete()
    audit.record(
        actor=actor,
        organization_id=site.organization_id,
        action="site.version.deleted",
        resource_type="site",
        resource_id=site.id,
        context={"slug": site.slug, "version": number},
    )


def delete_site(*, site: Site, actor) -> None:
    organization_id, site_id, slug = site.organization_id, site.id, site.slug
    if site.kind == Site.Kind.NODE:
        # The container, its network and images go first: a deleted site never leaves a running app behind.
        try:
            runner.remove(site)
        except (runner.RunnerUnavailable, runner.RunnerRefused) as exc:
            raise SiteError(f"The app could not be removed, so the site was kept: {exc}") from exc
    if site.application is not None:
        for credential in ApplicationCredential.objects.filter(
            service_account=site.application.service_account, revoked_at__isnull=True
        ):
            revoke_credential(credential=credential, actor=actor)
    for version in site.versions.all():
        _delete_files(version)
    site.delete()
    audit.record(
        actor=actor,
        organization_id=organization_id,
        action="site.deleted",
        resource_type="site",
        resource_id=site_id,
        context={"slug": slug},
    )


# ---------------------------------------------------------------- server apps (ADR-0020)


def _issue_app_token(site: Site, actor) -> str:
    """The app's identity towards IntraForge: an Application (created once) whose service account holds only
    what the owner grants it. Every deploy gets a fresh credential; earlier ones are revoked."""
    if site.application is None:
        site.application = register_application(
            organization=site.organization,
            name=f"Website: {site.name}"[:200],
            description=(
                f"The hosted server app at /{site.slug}/. It can reach only what is shared with this "
                "application (databases, file buckets, IntraForge Pay)."
            ),
            owner=actor,
        )
        site.save(update_fields=["application", "updated_at"])
    account = site.application.service_account
    for credential in ApplicationCredential.objects.filter(service_account=account, revoked_at__isnull=True):
        revoke_credential(credential=credential, actor=actor)
    _, token = issue_credential(service_account=account, actor=actor)
    return token


def _record_runtime(site: Site, result: dict | None, *, failure: str = "") -> None:
    if failure:
        site.runtime_state, site.runtime_log = "failed", failure[:4000]
    else:
        result = result or {}
        site.runtime_state = str(result.get("state") or "")[:40]
        site.runtime_log = str(result.get("log") or "")[:4000]
    site.save(update_fields=["runtime_state", "runtime_log", "updated_at"])


def _apply_version(site: Site, version: SiteVersion, actor) -> None:
    """Makes the active version live: a website is served by the backend view; a Node.js app is (re)built and
    started by the runner. A runner failure is recorded on the site (and audited), not raised: the version
    is stored either way and can be retried by activating it again."""
    if not version.manifest:
        if site.kind == Site.Kind.NODE:
            try:
                runner.remove(site)
            except (runner.RunnerUnavailable, runner.RunnerRefused) as exc:
                raise SiteError(f"The previous app could not be stopped: {exc}") from exc
        site.kind, site.runtime_state, site.runtime_log = Site.Kind.STATIC, "", ""
        site.save(update_fields=["kind", "runtime_state", "runtime_log", "updated_at"])
        return
    site.kind = Site.Kind.NODE
    site.save(update_fields=["kind", "updated_at"])
    token = _issue_app_token(site, actor)
    env = {"IF_API_URL": settings.SITES_APP_API_URL, "IF_API_TOKEN": token, "IF_SITE_NAME": site.name[:200]}
    try:
        result = runner.deploy(site=site, version=version, env=env)
        if site.status == Site.Status.DISABLED:
            result = runner.stop(site)
    except (runner.RunnerUnavailable, runner.RunnerRefused) as exc:
        _record_runtime(site, None, failure=str(exc))
        audit.record(
            actor=actor,
            organization_id=site.organization_id,
            action="site.app.failed",
            resource_type="site",
            resource_id=site.id,
            result=AuditEvent.Result.ERROR,
            context={"slug": site.slug, "version": version.number, "error": str(exc)[:300]},
        )
        return
    _record_runtime(site, result)
    audit.record(
        actor=actor,
        organization_id=site.organization_id,
        action="site.app.deployed",
        resource_type="site",
        resource_id=site.id,
        context={"slug": site.slug, "version": version.number, "state": site.runtime_state},
    )


def refresh_runtime(site: Site) -> Site:
    """Asks the runner how a server app is doing (best effort: the last answer stays if it does not reply)."""
    if site.kind == Site.Kind.NODE and runner.configured():
        try:
            _record_runtime(site, runner.status(site))
        except (runner.RunnerUnavailable, runner.RunnerRefused):
            pass
    return site


# ---------------------------------------------------------------- site names (ADR-0020 decision 3)

HOSTNAME_PATTERN = re.compile(
    r"^(?=.{4,253}$)([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$"
)
_IP = re.compile(r"^[0-9.]+$|:")


def _intraforge_names() -> set[str]:
    """IntraForge's own names: a site may be neither one of them nor a name under one."""
    names = {h.strip().lower().lstrip(".") for h in settings.ALLOWED_HOSTS if h.strip() and h.strip() != "*"}
    return names | {"localhost", "backend", "intraforge"}


def validate_hostname(hostname: str) -> str | None:
    hostname = (hostname or "").strip().lower().rstrip(".")
    if not hostname:
        return None
    if _IP.search(hostname) or not HOSTNAME_PATTERN.match(hostname):
        raise SiteError(
            "A site name is a name with a dot and no spaces, e.g. myshop.lan (letters, digits and hyphens)."
        )
    for own in _intraforge_names():
        if hostname == own or hostname.endswith("." + own):
            raise SiteError(f"'{hostname}' is IntraForge's own name or under it; choose a separate name.")
    return hostname


def set_hostname(*, site: Site, hostname: str, actor) -> Site:
    """Gives the site its own name on the shop network (or removes it). A Node.js app's proxy route
    follows."""
    new = validate_hostname(hostname)
    if new == site.hostname:
        return site
    if new and Site.objects.filter(hostname=new).exclude(pk=site.pk).exists():
        raise SiteError(f"The name '{new}' is already used by another site.")
    previous = site.hostname
    site.hostname = new
    try:
        site.save(update_fields=["hostname", "updated_at"])
    except IntegrityError as exc:
        raise SiteError(f"The name '{new}' is already used by another site.") from exc
    if site.kind == Site.Kind.NODE:
        try:
            runner.route(site)
        except (runner.RunnerUnavailable, runner.RunnerRefused) as exc:
            raise SiteError(f"The name was saved, but the app's route could not be updated: {exc}") from exc
    audit.record(
        actor=actor,
        organization_id=site.organization_id,
        action="site.hostname.changed",
        resource_type="site",
        resource_id=site.id,
        context={"slug": site.slug, "hostname": new, "previous": previous},
    )
    return site
