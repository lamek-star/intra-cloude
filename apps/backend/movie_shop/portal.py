"""The customer portal (ADR-0022 phase 3): a shop's customers sign up on the shop Wi-Fi, browse the catalogue,
place orders the counter charges, and collect Movie Shop points.

Portal customers are not IntraForge users. They sign in with a phone number and a password to one shop's
portal only; the session is a random token in an HttpOnly, SameSite=Strict cookie scoped to the portal API,
and this table keeps only its SHA-256. The owner approves a customer by adding them to IF Pay: Pay opens the
customer's wallet (and keeps its money and password). Points are a separate ledger that only ever takes
credits off Movie Shop purchases.
"""

import datetime
import hashlib
import logging
import re
import secrets
import unicodedata

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import APIException, AuthenticationFailed, ValidationError

from audit import services as audit
from service_apps import pay_bridge

from . import sales, scanning
from .models import MovieShop, PointsEntry, PortalCustomer, PortalSession, Sale, SaleLine

log = logging.getLogger(__name__)

SESSION_DAYS = 30
COOKIE = "ifportal"
COOKIE_PATH = "/api/v1/portal/"
MAX_OPEN_ORDERS = 3
_REFERRAL_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
# A real hash to check against when the phone number is unknown, so both answers take as long.
_DUMMY_HASH = make_password(secrets.token_urlsafe(16))


def normalize_phone(raw) -> str:
    text = str(raw or "").strip()
    digits = re.sub(r"[\s\-().]", "", text)
    if not re.fullmatch(r"\+?\d{7,15}", digits):
        raise ValidationError({"phone": "Enter your phone number (7 to 15 digits)."})
    return digits


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _new_session(customer: PortalCustomer) -> str:
    token = secrets.token_urlsafe(32)
    PortalSession.objects.create(
        token_hash=_hash(token),
        customer=customer,
        expires_at=timezone.now() + datetime.timedelta(days=SESSION_DAYS),
    )
    return token


def customer_for_token(shop: MovieShop, token: str | None) -> PortalCustomer | None:
    """The signed-in customer of this shop's portal, or None (no cookie, expired, signed out, rejected,
    blocked)."""
    if not token or len(token) > 100:
        return None
    session = (
        PortalSession.objects.select_related("customer")
        .filter(
            token_hash=_hash(token),
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
            customer__shop=shop,
        )
        .first()
    )
    if session is None or session.customer.status in (
        PortalCustomer.Status.REJECTED,
        PortalCustomer.Status.BLOCKED,
    ):
        return None
    return session.customer


def sign_out(token: str | None) -> None:
    if token:
        PortalSession.objects.filter(token_hash=_hash(token), revoked_at__isnull=True).update(
            revoked_at=timezone.now()
        )


def _referral_code(shop: MovieShop) -> str:
    for _ in range(20):
        code = "".join(secrets.choice(_REFERRAL_ALPHABET) for _ in range(6))
        if not shop.customers.filter(referral_code=code).exists():
            return code
    raise ValidationError({"detail": "Try again."})


def _birthday(value) -> datetime.date | None:
    if value in (None, ""):
        return None
    try:
        day = datetime.date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValidationError({"birthday": "A date, such as 1995-04-21."}) from exc
    if not datetime.date(1900, 1, 1) <= day <= timezone.localdate():
        raise ValidationError({"birthday": "A date in the past."})
    return day


def sign_up(shop: MovieShop, data: dict) -> tuple[PortalCustomer, str]:
    """A new customer, waiting for the owner. Signed in at once so they can look around."""
    name = scanning.clean_text(data.get("name"), "name", max_length=80)
    phone = normalize_phone(data.get("phone"))
    password = str(data.get("password") or "")
    if len(password) > 200:
        raise ValidationError({"password": "That password is too long."})
    try:
        validate_password(password)
    except DjangoValidationError as exc:
        raise ValidationError({"password": list(exc.messages)}) from exc
    referrer = None
    code = str(data.get("referral_code") or "").strip().upper()
    if code:
        referrer = shop.customers.filter(referral_code=code, status=PortalCustomer.Status.APPROVED).first()
        if referrer is None:
            raise ValidationError({"referral_code": "No customer of this shop has that code."})
    try:
        with transaction.atomic():
            customer = PortalCustomer.objects.create(
                shop=shop,
                name=name,
                phone=phone,
                password=make_password(password),
                birthday=_birthday(data.get("birthday")),
                referral_code=_referral_code(shop),
                referred_by=referrer,
            )
    except IntegrityError as exc:
        raise ValidationError(
            {"phone": "This phone number already has an account here. Sign in instead."}
        ) from exc
    audit.record(
        actor=None,
        organization_id=shop.organization_id,
        action="movie_shop.portal.sign_up",
        resource_type="movie_shop",
        resource_id=shop.id,
        context={"customer": str(customer.id), "referred": referrer is not None},
    )
    return customer, _new_session(customer)


def sign_in(shop: MovieShop, phone, password) -> tuple[PortalCustomer, str]:
    try:
        phone = normalize_phone(phone)
    except ValidationError:
        phone = ""
    customer = shop.customers.filter(phone=phone).first() if phone else None
    valid = check_password(str(password or "")[:200], customer.password if customer else _DUMMY_HASH)
    if (
        customer is None
        or not valid
        or customer.status
        in (
            PortalCustomer.Status.REJECTED,
            PortalCustomer.Status.BLOCKED,
        )
    ):
        audit.record(
            actor=None,
            organization_id=shop.organization_id,
            action="movie_shop.portal.sign_in",
            resource_type="movie_shop",
            resource_id=shop.id,
            result="denied",
            context={"customer": str(customer.id) if customer else ""},
        )
        raise AuthenticationFailed("Wrong phone number or password.")
    give_birthday_points(customer)
    return customer, _new_session(customer)


# ---- points ------------------------------------------------------------------------------------------------
def points_of(customer: PortalCustomer) -> int:
    return customer.points.aggregate(total=Sum("delta"))["total"] or 0


def _grant(customer: PortalCustomer, delta: int, reason: str, *, sale=None, note: str = "") -> None:
    if delta:
        PointsEntry.objects.create(customer=customer, delta=delta, reason=reason, sale=sale, note=note[:120])


def give_birthday_points(customer: PortalCustomer) -> None:
    """Once a year, in the customer's birthday month, at their first visit."""
    shop = customer.shop
    today = timezone.localdate()
    if not (
        shop.birthday_points
        and customer.status == PortalCustomer.Status.APPROVED
        and customer.birthday
        and customer.birthday.month == today.month
        and customer.birthday_points_year != today.year
    ):
        return
    with transaction.atomic():
        locked = PortalCustomer.objects.select_for_update().get(pk=customer.pk)
        if locked.birthday_points_year == today.year:
            return
        locked.birthday_points_year = today.year
        locked.save(update_fields=["birthday_points_year"])
        _grant(locked, shop.birthday_points, PointsEntry.Reason.BIRTHDAY, note=f"Happy birthday {today.year}")
    customer.birthday_points_year = today.year


def adjust_points(customer: PortalCustomer, *, actor, delta, note) -> None:
    if (
        isinstance(delta, bool)
        or not isinstance(delta, int)
        or not -100_000 <= delta <= 100_000
        or delta == 0
    ):
        raise ValidationError({"delta": "A whole number of points, not 0."})
    note = scanning.clean_text(note, "note", max_length=120)
    with transaction.atomic():
        locked = PortalCustomer.objects.select_for_update().get(pk=customer.pk)
        if points_of(locked) + delta < 0:
            raise ValidationError({"delta": "The customer does not have that many points."})
        _grant(locked, delta, PointsEntry.Reason.ADJUST, note=note)
    audit.record(
        actor=actor,
        organization_id=customer.shop.organization_id,
        action="movie_shop.customer.points_adjust",
        resource_type="movie_shop",
        resource_id=customer.shop_id,
        context={"customer": str(customer.id), "delta": delta, "note": note},
    )


def _free_lines(shop: MovieShop, customer: PortalCustomer, lines: list[SaleLine]) -> set[int]:
    """Indexes of the lines that are free: every Nth title the customer buys (the cheapest in the cart
    first)."""
    n = shop.every_nth_free
    if not n:
        return set()
    prior = SaleLine.objects.filter(
        sale__customer=customer, sale__status__in=[Sale.Status.PAID, Sale.Status.DONE]
    ).count()
    count = (prior + len(lines)) // n - prior // n
    cheapest = sorted(range(len(lines)), key=lambda i: (lines[i].price, i))
    return set(cheapest[:count])


def price_with_rewards(
    shop: MovieShop, customer: PortalCustomer | None, lines: list[SaleLine], use_points: bool
) -> dict:
    """What the customer pays: the free titles off, then their points (never more than the rest)."""
    free = _free_lines(shop, customer, lines) if customer else set()
    discount = sum(lines[i].price for i in free)
    subtotal = sum(line.price for line in lines) - discount
    points = min(points_of(customer), subtotal) if customer and use_points else 0
    return {"free": free, "discount": discount, "points_used": points, "total": subtotal - points}


def apply_rewards(sale: Sale, lines: list[SaleLine]) -> None:
    """At the counter's charge (inside its transaction, the sale locked): fixes the free titles and spends the
    points. The customer row is locked, so two charges for one customer cannot spend the same points."""
    customer = (
        PortalCustomer.objects.select_for_update().get(pk=sale.customer_id) if sale.customer_id else None
    )
    priced = price_with_rewards(sale.shop, customer, lines, sale.use_points)
    for i, line in enumerate(lines):
        line.free = i in priced["free"]
    SaleLine.objects.bulk_update(lines, ["free"])
    sale.discount = priced["discount"]
    sale.points_used = priced["points_used"]
    sale.total = priced["total"]
    if customer and sale.points_used:
        _grant(customer, -sale.points_used, PointsEntry.Reason.REDEEM, sale=sale, note=sale.number)


def return_points(sale: Sale, *, note: str) -> None:
    """A cancelled sale gives back the points it used (inside the cancelling transaction)."""
    if sale.customer_id and sale.points_used:
        _grant(sale.customer, sale.points_used, PointsEntry.Reason.RETURNED, sale=sale, note=note)


# ---- orders ------------------------------------------------------------------------------------------------
def place_order(customer: PortalCustomer, title_ids, use_points: bool) -> Sale:
    if customer.status != PortalCustomer.Status.APPROVED:
        raise ValidationError({"detail": "The shop has not approved your account yet."})
    shop = customer.shop
    lines = sales.build_lines(shop, title_ids)
    with transaction.atomic():
        locked = PortalCustomer.objects.select_for_update().get(pk=customer.pk)
        if locked.sales.filter(status=Sale.Status.ORDERED).count() >= MAX_OPEN_ORDERS:
            raise ValidationError(
                {"detail": f"You already have {MAX_OPEN_ORDERS} orders waiting at the counter."}
            )
        priced = price_with_rewards(shop, locked, lines, bool(use_points))
        sale = Sale.objects.create(
            shop=shop,
            number=sales.new_number(),
            status=Sale.Status.ORDERED,
            customer=locked,
            customer_name=locked.name,
            use_points=bool(use_points),
            total=priced["total"],  # an estimate; fixed when the counter charges it
            discount=priced["discount"],
            destination="",
            folder=sales.folder_name(shop.name),
        )
        for line in lines:
            line.sale = sale
        SaleLine.objects.bulk_create(lines)
    audit.record(
        actor=None,
        organization_id=shop.organization_id,
        action="movie_shop.portal.order",
        resource_type="movie_shop",
        resource_id=shop.id,
        context={"customer": str(customer.id), "sale": sale.number, "titles": len(lines)},
    )
    return sale


def cancel_order(customer: PortalCustomer, sale: Sale) -> Sale:
    if sale.customer_id != customer.id or sale.status != Sale.Status.ORDERED:
        raise ValidationError({"detail": "Only an order still waiting at the counter can be cancelled."})
    if not sales._cancel(sale, reason="cancelled by the customer"):
        raise ValidationError({"detail": "Only an order still waiting at the counter can be cancelled."})
    return sale


# ---- the owner ---------------------------------------------------------------------------------------------
def _username_for(customer: PortalCustomer) -> str:
    ascii_name = unicodedata.normalize("NFKD", customer.name).encode("ascii", "ignore").decode().lower()
    slug = re.sub(r"[^a-z0-9]+", ".", ascii_name).strip(".")[:30]
    return slug if len(slug) >= 3 else f"customer.{customer.phone[-4:]}"


def approve(customer: PortalCustomer, *, actor) -> dict:
    """Adds the customer to IF Pay: Pay opens their wallet (asking again opens the same one), then the
    customer is approved and the welcome and referral points are given. Returns Pay's answer, with the
    one-time first password only when the wallet was just opened (shown once to the owner, never stored)."""
    if customer.status not in (PortalCustomer.Status.PENDING, PortalCustomer.Status.APPROVED):
        raise ValidationError({"status": "Only a customer waiting for approval can be added to IF Pay."})
    wallet = pay_bridge.open_customer_wallet(
        sales.caller(customer.shop),
        actor_id=actor.pk,
        username=_username_for(customer),
        customer_name=customer.name,
        external_id=f"movie-customer:{customer.id}",
    )
    shop = customer.shop
    with transaction.atomic():
        locked = PortalCustomer.objects.select_for_update().get(pk=customer.pk)
        first_time = locked.status == PortalCustomer.Status.PENDING
        locked.pay_wallet_id = wallet["id"]
        locked.pay_username = str(wallet.get("username") or "")[:40]
        if first_time:
            locked.status = PortalCustomer.Status.APPROVED
            locked.approved_at = timezone.now()
            locked.approved_by = actor
            _grant(locked, shop.welcome_points, PointsEntry.Reason.WELCOME, note="Welcome")
            if locked.referred_by_id and shop.referral_points:
                referrer = PortalCustomer.objects.select_for_update().get(pk=locked.referred_by_id)
                if referrer.status == PortalCustomer.Status.APPROVED:
                    _grant(
                        referrer,
                        shop.referral_points,
                        PointsEntry.Reason.REFERRAL,
                        note=f"Invited {locked.name}",
                    )
        locked.save()
    customer.refresh_from_db()
    audit.record(
        actor=actor,
        organization_id=shop.organization_id,
        action="movie_shop.customer.approve",
        resource_type="movie_shop",
        resource_id=shop.id,
        context={
            "customer": str(customer.id),
            "wallet": str(wallet["id"]),
            "wallet_created": wallet["created"],
        },
    )
    return wallet


def set_status(customer: PortalCustomer, *, actor, status: str) -> PortalCustomer:
    """Reject a waiting customer, block one (signed out at once), or unblock one."""
    allowed = {
        PortalCustomer.Status.REJECTED: (PortalCustomer.Status.PENDING,),
        PortalCustomer.Status.BLOCKED: (PortalCustomer.Status.PENDING, PortalCustomer.Status.APPROVED),
    }
    status = {"reject": PortalCustomer.Status.REJECTED, "block": PortalCustomer.Status.BLOCKED}.get(
        status, status
    )
    if status == "unblock":
        if customer.status != PortalCustomer.Status.BLOCKED:
            raise ValidationError({"status": "This customer is not blocked."})
        new = PortalCustomer.Status.APPROVED if customer.pay_wallet_id else PortalCustomer.Status.PENDING
    elif status in allowed and customer.status in allowed[status]:
        new = status
    else:
        raise ValidationError({"status": "Not possible for this customer now."})
    with transaction.atomic():
        customer.status = new
        customer.save(update_fields=["status"])
        if new in (PortalCustomer.Status.REJECTED, PortalCustomer.Status.BLOCKED):
            customer.sessions.filter(revoked_at__isnull=True).update(revoked_at=timezone.now())
            for sale in customer.sales.filter(status=Sale.Status.ORDERED):
                sales._cancel(sale, reason=f"customer {new}")
    audit.record(
        actor=actor,
        organization_id=customer.shop.organization_id,
        action=f"movie_shop.customer.{'unblock' if status == 'unblock' else new}",
        resource_type="movie_shop",
        resource_id=customer.shop_id,
        context={"customer": str(customer.id)},
    )
    return customer


def set_portal(shop: MovieShop, *, actor, data: dict) -> MovieShop:
    fields = {
        "welcome_points": 100_000,
        "referral_points": 100_000,
        "birthday_points": 100_000,
        "every_nth_free": 100,
    }
    changed = []
    if "portal_open" in data:
        if not isinstance(data["portal_open"], bool):
            raise ValidationError({"portal_open": "true or false."})
        shop.portal_open = data["portal_open"]
        changed.append("portal_open")
    for name, top in fields.items():
        if name in data:
            value = data[name]
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= top:
                raise ValidationError({name: f"A whole number from 0 to {top}."})
            if name == "every_nth_free" and value == 1:
                raise ValidationError({name: "0 (off), or 2 or more."})
            setattr(shop, name, value)
            changed.append(name)
    if changed:
        shop.save(update_fields=changed)
        audit.record(
            actor=actor,
            organization_id=shop.organization_id,
            action="movie_shop.portal.settings",
            resource_type="movie_shop",
            resource_id=shop.id,
            context={name: getattr(shop, name) for name in changed},
        )
    return shop


def wallet_of(customer: PortalCustomer) -> dict | None:
    """The customer's IF Pay wallet as Pay reports it now (balance in credits), or None when Pay does not
    answer."""
    if not customer.pay_wallet_id:
        return None
    try:
        data = pay_bridge.customer_wallet(sales.caller(customer.shop), customer.pay_wallet_id)
    except APIException as exc:
        # Pay switched off or restarting: the portal still works, without the balance.
        log.info("IF Pay did not give the wallet of portal customer %s: %s", customer.id, exc)
        return {
            "username": customer.pay_username,
            "balance": None,
            "path": None,
            "must_change_password": False,
        }
    minor = data.get("balance_minor")
    return {
        "username": data.get("username") or customer.pay_username,
        "balance": (minor / 100) if isinstance(minor, int) else None,
        "path": data.get("wallet_path"),
        "must_change_password": bool(data.get("must_change_password")),
    }
