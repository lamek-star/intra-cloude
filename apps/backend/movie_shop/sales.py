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


def caller(shop: MovieShop) -> ApplicationCaller:
    """Who asks Pay: the shop (its agent application), on behalf of the person at the counter."""
    return ApplicationCaller(
        id=shop.agent_application_id,
        organization_id=shop.organization_id,
        app_type=APPLICATION_CALLER,
        product_name=shop.name[:120],
    )


def new_number() -> str:
    return f"MOV-{timezone.now():%Y%m%d}-{secrets.token_hex(3).upper()}"


def _drive_roots(shop: MovieShop) -> dict[str, dict]:
    return {d["root"].lower(): d for d in (shop.agent_report or {}).get("drives", [])}


def _check_titles(title_ids) -> None:
    if not isinstance(title_ids, list) or not 1 <= len(title_ids) <= MAX_TITLES_PER_SALE:
        raise ValidationError({"titles": f"Choose 1 to {MAX_TITLES_PER_SALE} titles."})


def build_lines(shop: MovieShop, title_ids) -> list[SaleLine]:
    """One unsaved line per title, as it is now (visible titles of this shop only), at its current price."""
    _check_titles(title_ids)
    titles = list(shop.titles.filter(id__in=title_ids, hidden=False).select_related("library"))
    if len(titles) != len(set(map(str, title_ids))):
        raise ValidationError({"titles": "Some titles are not in this shop's catalogue."})
    prices = {p.category.lower(): p.price for p in shop.category_prices.all()}
    return [
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


def _destination(shop: MovieShop, destination, needed_bytes: int) -> str:
    """The customer's drive, as the media agent reports it: not a shop library disk, with room for the
    titles."""
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
    if drive.get("free_bytes") is not None and needed_bytes > drive["free_bytes"]:
        raise ValidationError({"destination": "The customer's drive does not have room for these titles."})
    return drive["root"]


def counter_customer(shop: MovieShop, customer_id):
    """The approved portal customer of this shop a counter sale is for, or None when none is named."""
    from .models import PortalCustomer

    if customer_id in (None, ""):
        return None
    customer = (
        PortalCustomer.objects.filter(
            shop=shop, pk=customer_id, status=PortalCustomer.Status.APPROVED
        ).first()
        if _is_uuid(customer_id)
        else None
    )
    if customer is None:
        raise ValidationError({"customer": "Not an approved customer of this shop."})
    return customer


def create_sale(
    *,
    shop: MovieShop,
    actor,
    title_ids,
    destination,
    method: str,
    customer_name: str = "",
    customer_id=None,
    use_points: bool = False,
) -> Sale:
    """A counter sale. Naming an approved portal customer applies their rewards, as for their own portal
    orders: every Nth title free, and their points when ``use_points``."""
    from .portal import apply_rewards

    if method not in Sale.Method.values:
        raise ValidationError({"method": "ifpay or cash."})
    lines = build_lines(shop, title_ids)
    root = _destination(shop, destination, sum(line.size_bytes for line in lines))
    name = scanning.clean_text(customer_name, "customer_name", max_length=120, required=False)
    customer = counter_customer(shop, customer_id)
    with transaction.atomic():
        sale = Sale.objects.create(
            shop=shop,
            number=new_number(),
            method=method,
            customer_name=name or (customer.name if customer else ""),
            customer=customer,
            use_points=bool(use_points) and customer is not None,
            total=sum(line.price for line in lines),
            destination=root,
            folder=folder_name(shop.name),
            created_by=actor,
        )
        for line in lines:
            line.sale = sale
        SaleLine.objects.bulk_create(lines)
        if customer is not None:
            apply_rewards(sale, lines)
            sale.save(update_fields=["total", "discount", "points_used"])
    _start_payment(sale, actor)
    audit.record(
        actor=actor,
        organization_id=shop.organization_id,
        action="movie_shop.sale.create",
        resource_type="movie_shop",
        resource_id=shop.id,
        context={
            "sale": sale.number,
            "titles": len(lines),
            "total": sale.total,
            "method": method,
            "customer": str(customer.id) if customer else None,
            "points_used": sale.points_used,
        },
    )
    return sale


def _start_payment(sale: Sale, actor) -> None:
    """Nothing to pay: paid at once. IF Pay: ask Pay for the payment request. Cash: wait for "Paid in
    cash"."""
    if sale.total == 0:
        _mark_paid(sale, receipt="", actor=actor)
    elif sale.method == Sale.Method.IFPAY:
        _request_payment(sale, actor)


def charge_order(sale: Sale, *, actor, destination, method: str) -> Sale:
    """The counter charges a portal order once the customer brings their drive: the customer's rewards apply
    now (every Nth title free, then their points if they chose to use them), then the payment as for any
    sale."""
    from .portal import apply_rewards

    if method not in Sale.Method.values:
        raise ValidationError({"method": "ifpay or cash."})
    with transaction.atomic():
        sale = Sale.objects.select_for_update(of=("self",)).select_related("shop", "customer").get(pk=sale.pk)
        if sale.status != Sale.Status.ORDERED:
            raise ValidationError({"status": "This order has already been charged or cancelled."})
        lines = list(sale.lines.all())
        sale.destination = _destination(sale.shop, destination, sum(line.size_bytes for line in lines))
        sale.method = method
        sale.created_by = actor
        apply_rewards(sale, lines)
        sale.status = Sale.Status.AWAITING_PAYMENT
        sale.save(
            update_fields=[
                "destination",
                "method",
                "created_by",
                "status",
                "total",
                "discount",
                "points_used",
            ]
        )
    _start_payment(sale, actor)
    audit.record(
        actor=actor,
        organization_id=sale.shop.organization_id,
        action="movie_shop.order.charge",
        resource_type="movie_shop",
        resource_id=sale.shop_id,
        context={"sale": sale.number, "total": sale.total, "points_used": sale.points_used, "method": method},
    )
    return sale


def _request_payment(sale: Sale, actor) -> None:
    """Asks the shop's IntraForge Pay for the payment; the person at the counter must hold ifpay.checkout
    there."""
    result = pay_bridge.create_request(
        caller(sale.shop),
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
    status = pay_bridge.request_status(caller(sale.shop), sale.pay_request_id)
    if status.get("status") == "paid":
        with transaction.atomic():
            locked = Sale.objects.select_for_update().get(pk=sale.pk)
            if locked.status == Sale.Status.AWAITING_PAYMENT:
                _mark_paid(locked, receipt=str(status.get("receipt_number") or ""), actor=actor)
        sale.refresh_from_db()
    elif status.get("status") in ("expired", "cancelled"):
        _cancel(sale, reason="payment " + str(status.get("status")))
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


def _cancel(sale: Sale, *, reason: str) -> bool:
    """Cancels a sale not yet paid and gives back any points it used. False when it was no longer
    cancellable."""
    from .portal import return_points

    with transaction.atomic():
        locked = Sale.objects.select_for_update().get(pk=sale.pk)
        if locked.status not in (Sale.Status.ORDERED, Sale.Status.AWAITING_PAYMENT):
            return False
        locked.status = Sale.Status.CANCELLED
        locked.save(update_fields=["status"])
        return_points(locked, note=reason)
    sale.refresh_from_db()
    return True


def cancel(sale: Sale, *, actor) -> Sale:
    if not _cancel(sale, reason="cancelled at the counter"):
        raise ValidationError({"status": "Only a sale still waiting for its payment can be cancelled."})
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
