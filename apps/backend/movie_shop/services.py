"""Movie Shop business logic (ADR-0022). Views check who may do what; everything that changes data happens
here."""

import io

from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from applications import services as applications
from applications.models import ApplicationCredential
from audit import services as audit
from storage import services as storage
from storage.models import Bucket

from . import scanning
from .models import CategoryPrice, Library, MovieShop, Title

COVER_MAX_BYTES = 1_000_000
COVER_TYPES = {"image/jpeg", "image/png", "image/webp"}


def create_shop(*, actor, organization, project, name: str) -> MovieShop:
    name = scanning.clean_text(name, "name", max_length=120)
    if project.workspace.organization_id != organization.id:
        raise ValidationError({"project": "Choose a project of this organization."})
    if MovieShop.objects.filter(organization=organization, name=name).exists():
        raise ValidationError({"name": "This organization already has a movie shop with that name."})
    with transaction.atomic():
        agent = applications.register_application(
            organization=organization,
            name=f"{name} · media agent"[:200],
            description=(
                "The Movie Shop's media agent on the shop PC: reads the library folders "
                "and copies sold titles."
            ),
            owner=actor,
        )
        bucket_name = f"movie-covers-{name.lower()}"[:200]
        suffix = 1
        while Bucket.objects.filter(project=project, name=bucket_name).exists():
            suffix += 1
            bucket_name = f"movie-covers-{name.lower()}-{suffix}"[:200]
        bucket = Bucket.objects.create(project=project, name=bucket_name, created_by=actor)
        shop = MovieShop.objects.create(
            organization=organization,
            project=project,
            name=name,
            agent_application=agent,
            covers_bucket=bucket,
            created_by=actor,
        )
    audit.record(
        actor=actor,
        organization_id=organization.id,
        action="movie_shop.create",
        resource_type="movie_shop",
        resource_id=shop.id,
        context={"name": name},
    )
    return shop


def issue_agent_credential(*, shop: MovieShop, actor) -> str:
    """A new credential for the media agent; any earlier one stops working. Returns the token (shown once)."""
    service_account = shop.agent_application.service_account
    now = timezone.now()
    for credential in ApplicationCredential.objects.filter(
        service_account=service_account, revoked_at__isnull=True
    ):
        applications.revoke_credential(credential=credential, actor=actor)
    _, token = applications.issue_credential(service_account=service_account, actor=actor)
    audit.record(
        actor=actor,
        organization_id=shop.organization_id,
        action="movie_shop.agent_credential",
        resource_type="movie_shop",
        resource_id=shop.id,
        context={"at": now.isoformat()},
    )
    return token


def shop_for_agent(credential) -> MovieShop:
    """The shop whose media agent holds this credential, or None."""
    if not isinstance(credential, ApplicationCredential):
        return None
    application = credential.service_account.application
    return MovieShop.objects.filter(agent_application=application).first()


def record_agent_report(*, shop: MovieShop, data) -> dict:
    report = scanning.clean_drive_report(data)
    shop.agent_report = report
    shop.agent_seen_at = timezone.now()
    shop.save(update_fields=["agent_report", "agent_seen_at"])
    # Each library's drive sizes, from the drive it is on.
    for library in shop.libraries.all():
        drive = next(
            (d for d in report["drives"] if library.path.lower().startswith(d["root"].lower())), None
        )
        if drive:
            Library.objects.filter(pk=library.pk).update(
                total_bytes=drive["total_bytes"], free_bytes=drive["free_bytes"]
            )
    return agent_work(shop)


def agent_work(shop: MovieShop) -> dict:
    """What the agent should do now: every library, and which ones to scan."""
    return {
        "libraries": [
            {"id": str(lib.id), "path": lib.path, "scan": lib.scan_requested_at is not None}
            for lib in shop.libraries.all()
        ]
    }


def add_library(*, shop: MovieShop, actor, path: str, name: str = "", kind: str = "fixed") -> Library:
    path = scanning.clean_windows_path(path)
    if kind not in Library.Kind.values:
        raise ValidationError({"kind": "fixed, removable or network."})
    if shop.libraries.filter(path__iexact=path).exists():
        raise ValidationError({"path": "This folder is already a library of this shop."})
    name = scanning.clean_text(name or path, "name", max_length=120)
    library = Library.objects.create(
        shop=shop, path=path, name=name, kind=kind, scan_requested_at=timezone.now()
    )
    audit.record(
        actor=actor,
        organization_id=shop.organization_id,
        action="movie_shop.library.add",
        resource_type="movie_shop",
        resource_id=shop.id,
        context={"path": path},
    )
    return library


def request_scan(*, library: Library, actor) -> None:
    library.scan_requested_at = timezone.now()
    library.save(update_fields=["scan_requested_at"])


def remove_library(*, library: Library, actor) -> None:
    shop = library.shop
    path = library.path
    library.delete()
    audit.record(
        actor=actor,
        organization_id=shop.organization_id,
        action="movie_shop.library.remove",
        resource_type="movie_shop",
        resource_id=shop.id,
        context={"path": path},
    )


def start_scan(*, library: Library) -> int:
    with transaction.atomic():
        lib = Library.objects.select_for_update().get(pk=library.pk)
        lib.scan_generation = max(lib.scan_generation, lib.scanned_generation) + 1
        lib.save(update_fields=["scan_generation"])
    return lib.scan_generation


def add_scanned_titles(*, library: Library, generation: int, items) -> dict:
    """Upserts one batch of titles found by a scan. The owner's own values (price, hidden, description, and
    the title/year/category once edited by hand) are kept. Returns which titles want a cover uploaded."""
    if generation != library.scan_generation:
        raise ValidationError({"generation": "This scan was replaced by a newer one."})
    if not isinstance(items, list) or len(items) > scanning.MAX_TITLES_PER_BATCH:
        raise ValidationError({"titles": f"Send titles in batches of up to {scanning.MAX_TITLES_PER_BATCH}."})
    cleaned = [scanning.clean_title(item, i) for i, item in enumerate(items)]
    existing = {
        t.relative_path.lower(): t
        for t in library.titles.filter(relative_path__in=[c["relative_path"] for c in cleaned])
    }
    wanted = []
    with transaction.atomic():
        for c in cleaned:
            title = existing.get(c["relative_path"].lower())
            if title is None:
                title = Title(shop=library.shop, library=library, relative_path=c["relative_path"])
            if not title.edited:
                title.title, title.year, title.category = c["title"], c["year"], c["category"]
            title.kind, title.size_bytes, title.episodes = c["kind"], c["size_bytes"], c["episodes"]
            title.seen_generation = generation
            title.save()
            if c["cover_fingerprint"] and (
                title.cover_id is None or title.cover_fingerprint != c["cover_fingerprint"]
            ):
                wanted.append(c["relative_path"])
    return {"covers_wanted": wanted}


def finish_scan(*, library: Library, generation: int, message: str = "") -> dict:
    if generation != library.scan_generation:
        raise ValidationError({"generation": "This scan was replaced by a newer one."})
    with transaction.atomic():
        gone = library.titles.exclude(seen_generation=generation)
        removed = gone.count()
        gone.delete()
        Library.objects.filter(pk=library.pk).update(
            scanned_generation=generation,
            scan_requested_at=None,
            last_scan_at=timezone.now(),
            last_scan_message=scanning.clean_text(message, "message", max_length=300, required=False),
        )
    return {"titles": library.titles.count(), "removed": removed}


def attach_cover(*, library: Library, relative_path: str, fingerprint: str, upload) -> Title:
    relative_path = scanning.clean_relative_path(relative_path)
    title = library.titles.filter(relative_path__iexact=relative_path).first()
    if title is None:
        raise ValidationError({"relative_path": "No such title in this library."})
    if upload is None or upload.size > COVER_MAX_BYTES:
        raise ValidationError({"file": f"A picture up to {COVER_MAX_BYTES // 1000} KB."})
    head = upload.read(16)
    upload.seek(0)
    if not (
        head.startswith(b"\xff\xd8\xff")
        or head.startswith(b"\x89PNG\r\n\x1a\n")
        or (head[:4] == b"RIFF" and head[8:12] == b"WEBP")
    ):
        raise ValidationError({"file": "A JPEG, PNG or WebP picture."})
    shop = library.shop
    creator = shop.agent_application.service_account.identity_user
    old = title.cover
    cover = storage.upload_file(
        bucket=shop.covers_bucket,
        folder=None,
        uploaded_file=upload,
        display_filename=f"{title.title[:180]}.jpg",
        creator=creator,
    )
    if cover.mime_type not in COVER_TYPES:
        storage.delete_file(cover, actor=creator)
        raise ValidationError({"file": "A JPEG, PNG or WebP picture."})
    title.cover = cover
    title.cover_fingerprint = scanning.clean_text(fingerprint, "fingerprint", max_length=64, required=False)
    title.save(update_fields=["cover", "cover_fingerprint", "updated_at"])
    if old is not None:
        storage.delete_file(old, actor=creator)
    return title


def price_of(title: Title, category_prices: dict[str, int], default: int) -> int:
    if title.price is not None:
        return title.price
    return category_prices.get(title.category.lower(), default)


def category_summary(shop: MovieShop, library: Library | None = None) -> list[dict]:
    qs = shop.titles.filter(hidden=False)
    if library is not None:
        qs = qs.filter(library=library)
    rows = qs.values("category").annotate(count=Count("id"), size=Sum("size_bytes")).order_by("category")
    return [{"name": r["category"], "count": r["count"], "size_bytes": r["size"] or 0} for r in rows]


def set_prices(*, shop: MovieShop, actor, default_price, categories) -> None:
    if (
        isinstance(default_price, bool)
        or not isinstance(default_price, int)
        or not 0 <= default_price <= 1_000_000
    ):
        raise ValidationError({"default_price": "A price in credits."})
    if not isinstance(categories, dict) or len(categories) > 200:
        raise ValidationError({"categories": "Category prices as {category: credits}."})
    clean = {}
    for name, price in categories.items():
        category = scanning.clean_text(name, "categories", max_length=120)
        if isinstance(price, bool) or not isinstance(price, int) or not 0 <= price <= 1_000_000:
            raise ValidationError({"categories": f"{category}: a price in credits."})
        clean[category] = price
    with transaction.atomic():
        shop.default_price = default_price
        shop.save(update_fields=["default_price"])
        shop.category_prices.all().delete()
        CategoryPrice.objects.bulk_create(
            [CategoryPrice(shop=shop, category=c, price=p) for c, p in clean.items()]
        )
    audit.record(
        actor=actor,
        organization_id=shop.organization_id,
        action="movie_shop.prices",
        resource_type="movie_shop",
        resource_id=shop.id,
        context={"default": default_price, "categories": len(clean)},
    )


def edit_title(*, title: Title, actor, data: dict) -> Title:
    fields = []
    if "title" in data:
        title.title = scanning.clean_text(data["title"], "title", max_length=200)
        title.edited = True
        fields += ["title", "edited"]
    if "year" in data:
        year = data["year"]
        if year is not None and (
            isinstance(year, bool) or not isinstance(year, int) or not 1880 <= year <= 2100
        ):
            raise ValidationError({"year": "A year such as 2025."})
        title.year = year
        title.edited = True
        fields += ["year", "edited"]
    if "category" in data:
        title.category = scanning.clean_text(data["category"], "category", max_length=120)
        title.edited = True
        fields += ["category", "edited"]
    if "price" in data:
        price = data["price"]
        if price is not None and (
            isinstance(price, bool) or not isinstance(price, int) or not 0 <= price <= 1_000_000
        ):
            raise ValidationError({"price": "A price in credits, or empty for the category's price."})
        title.price = price
        fields.append("price")
    if "hidden" in data:
        if not isinstance(data["hidden"], bool):
            raise ValidationError({"hidden": "true or false."})
        title.hidden = data["hidden"]
        fields.append("hidden")
    if "description" in data:
        title.description = scanning.clean_text(
            data["description"], "description", max_length=2000, required=False
        )
        fields.append("description")
    if fields:
        title.save(update_fields=[*set(fields), "updated_at"])
        audit.record(
            actor=actor,
            organization_id=title.shop.organization_id,
            action="movie_shop.title.edit",
            resource_type="movie_shop",
            resource_id=title.shop_id,
            context={"title": str(title.id), "fields": sorted(set(fields))},
        )
    return title


def read_cover(title: Title) -> tuple[bytes, str] | None:
    if title.cover is None or title.cover.status != "active":
        return None
    from storage.backends import get_client

    body = get_client().get_stream(title.cover.object_key)
    data = io.BytesIO(body.read(COVER_MAX_BYTES + 1)).getvalue()
    return data, title.cover.mime_type
