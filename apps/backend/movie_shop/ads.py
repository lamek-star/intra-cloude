"""Ads on a shop's customer portal (ADR-0022 decision 8, phase 4).

An ad is the shop's own record -- a title, a short text, who it is for, a picture, dates -- shown only on that
shop's portal. A tap opens one of the shop's own films or a web address; only http and https addresses are
accepted, and the portal opens them in a new tab with no referrer. Pictures are ordinary IntraForge files in
the shop's covers bucket, checked to be a real JPEG, PNG or WebP picture. The portal counts views and taps;
nobody is tracked.
"""

import datetime
from urllib.parse import urlsplit

from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from audit import services as audit
from storage import services as storage

from . import scanning, services
from .models import Ad, MovieShop

MAX_ADS_PER_SHOP = 50
PICTURE_MAX_BYTES = 2_000_000
_FIELDS = ("title", "text", "advertiser", "film", "link", "starts_on", "ends_on", "active", "position")


def _date(value, field: str):
    if value in (None, ""):
        return None
    try:
        return datetime.date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValidationError({field: "A date, such as 2026-12-01."}) from exc


def _link(value) -> str:
    link = str(value or "").strip()
    if not link:
        return ""
    if len(link) > 300:
        raise ValidationError({"link": "Up to 300 characters."})
    parts = urlsplit(link)
    if parts.scheme not in ("http", "https") or not parts.netloc or any(c in link for c in " <>\"'\\"):
        raise ValidationError({"link": "A web address starting with http:// or https://."})
    return link


def _apply(ad: Ad, data: dict, *, creating: bool) -> None:
    if not isinstance(data, dict):
        raise ValidationError({"detail": "An object."})
    unknown = set(data) - set(_FIELDS)
    if unknown:
        raise ValidationError({"detail": f"Unknown fields: {', '.join(sorted(unknown))}."})
    if creating or "title" in data:
        ad.title = scanning.clean_text(data.get("title"), "title", max_length=80)
    if "text" in data:
        ad.text = scanning.clean_text(data.get("text"), "text", max_length=300, required=False)
    if "advertiser" in data:
        ad.advertiser = scanning.clean_text(
            data.get("advertiser"), "advertiser", max_length=80, required=False
        )
    if "link" in data:
        ad.link = _link(data.get("link"))
    if "film" in data:
        film = data.get("film")
        if film in (None, ""):
            ad.film = None
        else:
            found = ad.shop.titles.filter(id=film).first() if _is_uuid(film) else None
            if found is None:
                raise ValidationError({"film": "Not a film of this shop."})
            ad.film = found
    if "starts_on" in data:
        ad.starts_on = _date(data.get("starts_on"), "starts_on")
    if "ends_on" in data:
        ad.ends_on = _date(data.get("ends_on"), "ends_on")
    if "active" in data:
        if not isinstance(data["active"], bool):
            raise ValidationError({"active": "true or false."})
        ad.active = data["active"]
    if "position" in data:
        pos = data["position"]
        if isinstance(pos, bool) or not isinstance(pos, int) or not 0 <= pos <= 10_000:
            raise ValidationError({"position": "A whole number from 0 to 10000."})
        ad.position = pos
    if ad.film_id and ad.link:
        raise ValidationError({"link": "Choose a film or a web address, not both."})
    if ad.starts_on and ad.ends_on and ad.ends_on < ad.starts_on:
        raise ValidationError({"ends_on": "The last day is before the first day."})


def _is_uuid(value) -> bool:
    import uuid

    try:
        uuid.UUID(str(value))
        return True
    except ValueError:
        return False


def _audit(ad: Ad, actor, action: str, **context) -> None:
    audit.record(
        actor=actor,
        organization_id=ad.shop.organization_id,
        action=f"movie_shop.ad.{action}",
        resource_type="movie_shop",
        resource_id=ad.shop_id,
        context={"ad": str(ad.id), "title": ad.title, **context},
    )


def create_ad(shop: MovieShop, *, actor, data: dict) -> Ad:
    with transaction.atomic():
        MovieShop.objects.select_for_update().get(pk=shop.pk)
        if shop.ads.count() >= MAX_ADS_PER_SHOP:
            raise ValidationError(
                {"detail": f"A shop keeps at most {MAX_ADS_PER_SHOP} ads; delete an old one."}
            )
        ad = Ad(shop=shop, created_by=actor)
        _apply(ad, data, creating=True)
        ad.save()
    _audit(ad, actor, "create")
    return ad


def update_ad(ad: Ad, *, actor, data: dict) -> Ad:
    _apply(ad, data, creating=False)
    ad.save()
    _audit(ad, actor, "update", fields=sorted(data) if isinstance(data, dict) else [])
    return ad


def delete_ad(ad: Ad, *, actor) -> None:
    picture = ad.picture
    _audit(ad, actor, "delete")
    ad.delete()
    if picture is not None:
        storage.delete_file(picture, actor=_files_identity(ad.shop))


def _files_identity(shop: MovieShop):
    """The shop's own identity for its pictures (the media agent's service account, as for covers)."""
    return shop.agent_application.service_account.identity_user


def set_picture(ad: Ad, *, actor, upload) -> Ad:
    if upload is None or upload.size > PICTURE_MAX_BYTES:
        raise ValidationError({"file": f"A picture up to {PICTURE_MAX_BYTES // 1_000_000} MB."})
    head = upload.read(16)
    upload.seek(0)
    if not (
        head.startswith(b"\xff\xd8\xff")
        or head.startswith(b"\x89PNG\r\n\x1a\n")
        or (head[:4] == b"RIFF" and head[8:12] == b"WEBP")
    ):
        raise ValidationError({"file": "A JPEG, PNG or WebP picture."})
    shop = ad.shop
    identity = _files_identity(shop)
    picture = storage.upload_file(
        bucket=shop.covers_bucket,
        folder=None,
        uploaded_file=upload,
        display_filename=f"ad-{ad.id}",
        creator=identity,
    )
    if picture.mime_type not in services.COVER_TYPES:
        storage.delete_file(picture, actor=identity)
        raise ValidationError({"file": "A JPEG, PNG or WebP picture."})
    old = ad.picture
    ad.picture = picture
    ad.save(update_fields=["picture"])
    if old is not None:
        storage.delete_file(old, actor=identity)
    _audit(ad, actor, "picture")
    return ad


def read_picture(ad: Ad) -> tuple[bytes, str] | None:
    return services.read_file(ad.picture, PICTURE_MAX_BYTES)


def showing(shop: MovieShop):
    """The ads on the portal today: switched on, within their dates."""
    today = timezone.localdate()
    return (
        shop.ads.filter(active=True)
        .filter(Q(starts_on__isnull=True) | Q(starts_on__lte=today))
        .filter(Q(ends_on__isnull=True) | Q(ends_on__gte=today))
        .select_related("film")
    )


def count_views(ads: list[Ad]) -> None:
    if ads:
        Ad.objects.filter(id__in=[a.id for a in ads]).update(views=F("views") + 1)


def count_tap(ad: Ad) -> None:
    Ad.objects.filter(id=ad.id).update(taps=F("taps") + 1)
