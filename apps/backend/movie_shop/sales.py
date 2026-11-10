"""Counter sales (ADR-0022 phase 2): a cart of titles for one customer, paid through IntraForge Pay (the
existing Pay bridge, ADR-0018) or in cash, then copied by the media agent onto the customer's drive.

Money never moves here: a Pay payment is a payment request the customer confirms in their own wallet, and
the sale only records what Pay answers. The copy starts only once the sale is paid."""

import re
import secrets
import uuid

from django.db import transaction
from django.http import Http404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError

from audit import services as audit
from service_apps import pay_bridge
from service_apps.app_pay import APPLICATION_CALLER, ApplicationCaller

from . import scanning, services
from .models import MovieShop, Sale, SaleLine

MAX_TITLES_PER_SALE = 100
_UNSAFE_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def folder_name(shop_name: str) -> str:
    """The shop's name as a Windows folder name ("Lamek Movie Shop")."""
    name = _UNSAFE_NAME.sub(" ", shop_name).strip(" .") or "Movie Shop"
    return re.sub(r"\s+", " ", name)[:120]


def _caller(shop: MovieShop) -> ApplicationCaller:
    """Who asks Pay: the shop (its agent application), on behalf of the person at the counter."""
    return ApplicationCaller(
        id=shop.agent_application_id,
        organization_id=shop.organization_id,
        app_type=APPLICATION_CALLER,
        product_name=shop.name[:120],
    )


def _new_number() -> str:
    return f"MOV-{timezone.now():%Y%m%d}-{secrets.token_hex(3).upper()}"


def _drive_roots(shop: MovieShop) -> dict[str, dict]:
    return {d["root"].lower(): d for d in (shop.agent_report or {}).get("drives", [])}


def create_sale(
    *, shop: MovieShop, actor, title_ids, destination, method: str, customer_name: str = ""
) -> Sale:
    if method not in Sale.Method.values:
        raise ValidationError({"method": "ifpay or cash."})
    if not isinstance(title_ids, list) or not 1 <= len(title_ids) <= MAX_TITLES_PER_SALE:
        raise ValidationError({"titles": f"Choose 1 to {MAX_TITLES_PER_SALE} titles."})
    destination = scanning.clean_windows_path(destination, "destination")
    drive = _drive_roots(shop).get(destination.lower())
    if drive is None:
        raise ValidationError(
            {"destination": "Choose a drive the media agent sees on the shop PC (plug it in first)."}
        )
    if any(
        lib.path.lower().startswith(drive["root"].lower()) and drive["kind"] != "removable"
        for lib in shop.libraries.all()
    ):
        # Copying onto the library's own fixed disk would only duplicate the shop's files.
        raise ValidationError(
            {"destination": "Choose the customer's drive, not one of the shop's library drives."}
        )
    titles = list(shop.titles.filter(id__in=title_ids, hidden=False).select_related("library"))
    if len(titles) != len(set(map(str, title_ids))):
        raise ValidationError({"titles": "Some titles are not in this shop's catalogue."})
    prices = {p.category.lower(): p.price for p in shop.category_prices.all()}
    lines = [
        SaleLine(
            title=t,
            library=t.library,
            title_name=t.title,
            category=t.category,
            relative_path=t.relative_path,
            kind=t.kind,
            price=services.price_of(t, prices, shop.default_price),
            size_bytes=t.size_bytes,
        )
        for t in titles
    ]
    total = sum(line.price for line in lines)
    needed = sum(line.size_bytes for line in lines)
    if drive.get("free_bytes") is not None and needed > drive["free_bytes"]:
        raise ValidationError({"destination": "The customer's drive does not have room for these titles."})
    name = scanning.clean_text(customer_name, "customer_name", max_length=120, required=False)
    with transaction.atomic():
        sale = Sale.objects.create(
            shop=shop,
            number=_new_number(),
            method=method,
            customer_name=name,
            total=total,
            destination=drive["root"],
            folder=folder_name(shop.name),
            created_by=actor,
        )
        for line in lines:
            line.sale = sale
        SaleLine.objects.bulk_create(lines)
    if method == Sale.Method.IFPAY:
        if total == 0:
            _mark_paid(sale, receipt="", actor=actor)
        else:
            _request_payment(sale, actor)
    audit.record(
        actor=actor,
        organization_id=shop.organization_id,
        action="movie_shop.sale.create",
        resource_type="movie_shop",
        resource_id=shop.id,
        context={"sale": sale.number, "titles": len(lines), "total": total, "method": method},
    )
    return sale


def _request_payment(sale: Sale, actor) -> None:
    """Asks the shop's IntraForge Pay for the payment; the person at the counter must hold ifpay.checkout
    there."""
    result = pay_bridge.create_request(
        _caller(sale.shop),
        actor_id=actor.pk,
        amount_minor=sale.total * 100,
        reference=f"{sale.shop.name} · {sale.number}"[:120],
        external_id=sale.number,
    )
    sale.pay_request_id = result.get("id")
    sale.pay_code = str(result.get("code") or "")
    sale.pay_qr_svg = str(result.get("qr_svg") or "")[:200_000]
    expires = result.get("expires_at")
    sale.pay_expires_at = parse_datetime(expires) if isinstance(expires, str) else None
    sale.save(update_fields=["pay_request_id", "pay_code", "pay_qr_svg", "pay_expires_at"])


def _mark_paid(sale: Sale, *, receipt: str, actor) -> None:
    sale.status = Sale.Status.PAID
    sale.receipt_number = receipt[:60]
    sale.paid_at = timezone.now()
    sale.save(update_fields=["status", "receipt_number", "paid_at"])
    audit.record(
        actor=actor,
        organization_id=sale.shop.organization_id,
        action="movie_shop.sale.paid",
        resource_type="movie_shop",
        resource_id=sale.shop_id,
        context={"sale": sale.number, "method": sale.method, "receipt": sale.receipt_number},
    )


def refresh_payment(sale: Sale, *, actor) -> Sale:
    """For a sale waiting for an IF Pay payment, asks Pay where it stands (paid, expired, cancelled)."""
    if (
        sale.status != Sale.Status.AWAITING_PAYMENT
        or sale.method != Sale.Method.IFPAY
        or not sale.pay_request_id
    ):
        return sale
    status = pay_bridge.request_status(_caller(sale.shop), sale.pay_request_id)
    if status.get("status") == "paid":
        with transaction.atomic():
            locked = Sale.objects.select_for_update().get(pk=sale.pk)
            if locked.status == Sale.Status.AWAITING_PAYMENT:
                _mark_paid(locked, receipt=str(status.get("receipt_number") or ""), actor=actor)
        sale.refresh_from_db()
    elif status.get("status") in ("expired", "cancelled"):
        sale.status = Sale.Status.CANCELLED
        sale.save(update_fields=["status"])
    return sale


def mark_cash(sale: Sale, *, actor) -> Sale:
    """The customer paid in cash at the counter instead (the person holding movies.sell says so)."""
    if sale.status != Sale.Status.AWAITING_PAYMENT:
        raise ValidationError({"status": "This sale is not waiting for a payment."})
    with transaction.atomic():
        locked = Sale.objects.select_for_update().get(pk=sale.pk)
        if locked.status != Sale.Status.AWAITING_PAYMENT:
            raise ValidationError({"status": "This sale is not waiting for a payment."})
        locked.method = Sale.Method.CASH
        locked.save(update_fields=["method"])
        _mark_paid(locked, receipt="", actor=actor)
    sale.refresh_from_db()
    return sale


def cancel(sale: Sale, *, actor) -> Sale:
    if sale.status != Sale.Status.AWAITING_PAYMENT:
        raise ValidationError({"status": "Only a sale still waiting for its payment can be cancelled."})
    sale.status = Sale.Status.CANCELLED
    sale.save(update_fields=["status"])
    audit.record(
        actor=actor,
        organization_id=sale.shop.organization_id,
        action="movie_shop.sale.cancel",
        resource_type="movie_shop",
        resource_id=sale.shop_id,
        context={"sale": sale.number},
    )
    return sale


def retry_failed(sale: Sale, *, actor) -> Sale:
    if sale.status != Sale.Status.PAID:
        raise ValidationError({"status": "Only a paid sale can be copied again."})
    sale.lines.filter(copy_status=SaleLine.Copy.FAILED).update(
        copy_status=SaleLine.Copy.WAITING, copied_bytes=0, copy_message=""
    )
    return sale


# ---- the media agent's side ----------------------------------------------------------------------------
def copy_work(shop: MovieShop) -> list[dict]:
    """The titles of paid sales still to copy, with where they are and where they go."""
    out = []
    lines = (
        SaleLine.objects.filter(
            sale__shop=shop,
            sale__status=Sale.Status.PAID,
            copy_status__in=[SaleLine.Copy.WAITING, SaleLine.Copy.COPYING],
        )
        .select_related("sale", "library")
        .order_by("sale__paid_at", "title_name")[:50]
    )
    for line in lines:
        if line.library is None:
            continue
        out.append(
            {
                "line": str(line.id),
                "sale": line.sale.number,
                "library": line.library.path,
                "relative_path": line.relative_path,
                "kind": line.kind,
                "size_bytes": line.size_bytes,
                "destination": line.sale.destination,
                "folder": f"{line.sale.folder}\\{folder_name(line.category)}",
            }
        )
    return out


def copy_progress(*, shop: MovieShop, line_id, data) -> SaleLine:
    line = (
        SaleLine.objects.select_related("sale").filter(id=line_id, sale__shop=shop).first()
        if _is_uuid(line_id)
        else None
    )
    if line is None:
        raise Http404
    status = data.get("status") if isinstance(data, dict) else None
    if status not in (SaleLine.Copy.COPYING, SaleLine.Copy.COPIED, SaleLine.Copy.FAILED):
        raise ValidationError({"status": "copying, copied or failed."})
    if line.sale.status != Sale.Status.PAID:
        raise ValidationError({"status": "This sale is not paid, so nothing is copied."})
    copied = scanning.clean_bytes(data.get("copied_bytes"), "copied_bytes") or 0
    with transaction.atomic():
        line.copy_status = status
        line.copied_bytes = copied
        line.copy_message = scanning.clean_text(
            data.get("message"), "message", max_length=300, required=False
        )
        line.copy_updated_at = timezone.now()
        line.save(update_fields=["copy_status", "copied_bytes", "copy_message", "copy_updated_at"])
        sale = Sale.objects.select_for_update().get(pk=line.sale_id)
        if (
            sale.status == Sale.Status.PAID
            and not sale.lines.exclude(copy_status=SaleLine.Copy.COPIED).exists()
        ):
            sale.status = Sale.Status.DONE
            sale.save(update_fields=["status"])
    return line


def _is_uuid(value) -> bool:
    try:
        uuid.UUID(str(value))
        return True
    except ValueError:
        return False
