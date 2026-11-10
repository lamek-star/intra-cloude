"""Taking an IntraForge Pay payment on another application's behalf (ADR-0018, amended 2026-10-24).

A service application -- today Spare Parts, for an invoice -- asks IntraForge, with its own service
token, to have IntraForge Pay charge a customer. IntraForge, not the caller, decides:

* which Pay: the one installed in the caller's OWN organization (never another shop's);
* who: the person named must be an active member there and hold ``ifpay.checkout`` on that Pay;
* how: IntraForge calls that Pay's internal API with the Pay deployment's own service token, which
  only IntraForge and that Pay hold. The caller never learns it and never reaches Pay directly.

Pay records the asking application on the request and answers status questions only to it. The
customer still confirms the exact amount in their own wallet; nothing here moves money or marks
anything paid. Pay's internal address comes from this installation's settings, never from a request.
"""

import json
import urllib.error
import urllib.request
import uuid

from rest_framework.exceptions import APIException, NotFound, PermissionDenied, ValidationError

from organizations.models import Membership

from .deployments import Deployment, get_deployment
from .models import ServiceApp
from .sessions import capabilities_for, display_name
from .types import get_type

PAY_TYPE = "intraforge_pay"
TIMEOUT_SECONDS = 8.0
MAX_REFERENCE = 120


class PayUnavailable(APIException):
    status_code = 503
    default_detail = "IntraForge Pay is not answering. Try again in a moment."
    default_code = "pay_unavailable"


class PayRefused(APIException):
    status_code = 409
    default_code = "pay_refused"


def _caller_name(caller) -> str:
    """The asking application's product name ("Spare Parts"), or an Application's own name (app_pay.py)."""
    return getattr(caller, "product_name", None) or get_type(caller.app_type).product_name


def pay_for(caller: ServiceApp, *, reading: bool = False) -> tuple[ServiceApp, Deployment]:
    """The Pay installed in the caller's own organization (enabled, deployed), or a refusal. Reading a
    status is allowed while Pay is switched off: a customer may already have paid."""
    if caller.app_type == PAY_TYPE:
        raise PermissionDenied("IntraForge Pay cannot ask itself for a payment.")
    candidates = list(
        ServiceApp.objects.filter(
            organization_id=caller.organization_id, app_type=PAY_TYPE, removed_at__isnull=True
        )
    )
    if not candidates:
        raise NotFound("IntraForge Pay is not installed in this shop.")
    if len(candidates) > 1:
        raise PayRefused("More than one IntraForge Pay is installed in this shop; choose one first.")
    pay = candidates[0]
    if not pay.enabled and not reading:
        raise PayRefused("IntraForge Pay is switched off in this shop.")
    deployment = get_deployment(pay.deployment)
    if deployment is None or not deployment.token:
        raise PayUnavailable("IntraForge Pay's service is not part of this installation.")
    return pay, deployment


def _cashier(pay: ServiceApp, actor_id):
    """The person, if they are an active member of Pay's organization and may take payments there."""
    return _member_holding(
        pay,
        actor_id,
        "ifpay.checkout",
        "This person may not take IntraForge Pay payments. Give them the Pay Cashier role.",
    )


def _member_holding(pay: ServiceApp, actor_id, capability: str, refusal: str):
    """The person, if they are an active member of Pay's organization and hold `capability` on that Pay."""
    try:
        uid = uuid.UUID(str(actor_id))
    except (TypeError, ValueError) as exc:
        raise ValidationError({"actorId": "Name the person taking the payment."}) from exc
    membership = (
        Membership.objects.select_related("user")
        .filter(
            organization_id=pay.organization_id,
            user_id=uid,
            status=Membership.Status.ACTIVE,
            user__is_active=True,
        )
        .first()
    )
    if membership is None:
        raise PermissionDenied("This person is not a member of this shop.")
    caps = capabilities_for(membership.user, pay)
    if capability not in caps:
        raise PermissionDenied(refusal)
    return membership.user, caps


def _call(deployment: Deployment, method: str, path: str, body: dict | None = None) -> dict:
    url = f"{deployment.internal_url}{deployment.launch_path}internal/{path}"
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(  # noqa: S310 (fixed internal URL from settings)
        url,
        data=data,
        method=method,
        headers={
            "X-IntraForge-Service-Token": deployment.token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as resp:  # noqa: S310
            return json.loads(resp.read(1_000_000) or b"{}")
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read(10_000) or b"{}")
        except ValueError:
            detail = {}
        message = str(detail.get("message") or "IntraForge Pay refused the request.")[:300]
        if exc.code == 404:
            raise NotFound(message) from exc
        if exc.code in (401, 503):
            raise PayUnavailable() from exc
        if exc.code == 403:
            raise PermissionDenied(message) from exc
        raise PayRefused(message) from exc
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise PayUnavailable() from exc


_PUBLIC = (
    "id",
    "status",
    "amount",
    "amount_minor",
    "reference",
    "receipt_number",
    "paid_at",
    "expires_at",
    "created_at",
    "notice",
)


def _public(data: dict, *, with_code: bool) -> dict:
    out = {k: data.get(k) for k in _PUBLIC}
    out["merchant"] = {"name": (data.get("merchant") or {}).get("name")}
    if with_code:
        out["code"] = data.get("code")
        out["qr_svg"] = data.get("qr_svg")
    return out


def create_request(caller: ServiceApp, *, actor_id, amount_minor, reference, external_id) -> dict:
    pay, deployment = pay_for(caller)
    user, caps = _cashier(pay, actor_id)
    if not isinstance(amount_minor, int) or isinstance(amount_minor, bool) or amount_minor <= 0:
        raise ValidationError({"amountMinor": "Enter an amount greater than zero."})
    reference = str(reference or "").strip()
    external_id = str(external_id or "").strip()
    if not reference or len(reference) > MAX_REFERENCE:
        raise ValidationError(
            {"reference": f"Say what the payment is for (up to {MAX_REFERENCE} characters)."}
        )
    if not external_id or len(external_id) > MAX_REFERENCE:
        raise ValidationError({"externalId": "Name the record the payment is for."})
    data = _call(
        deployment,
        "POST",
        "payment-requests",
        {
            "actor": {"id": str(user.pk), "display_name": display_name(user), "capabilities": caps},
            "amount_minor": amount_minor,
            "reference": reference,
            # The application's product name ("Spare Parts"): the customer already sees the shop's name.
            "source": {
                "app_id": str(caller.id),
                "app_name": _caller_name(caller),
                "external_id": external_id,
            },
        },
    )
    return {
        "pay": {"id": str(pay.id), "display_name": pay.display_name},
        "user": user,
        **_public(data, with_code=True),
    }


def request_status(caller: ServiceApp, request_id) -> dict:
    try:
        rid = uuid.UUID(str(request_id))
    except ValueError as exc:
        raise NotFound("No such payment request.") from exc
    _, deployment = pay_for(caller, reading=True)
    data = _call(deployment, "GET", f"payment-requests/{rid}?source_app_id={caller.id}")
    return _public(data, with_code=False)


# ---- customer wallets opened for an application (ADR-0022: the Movie Shop's portal customers) --------------
_CUSTOMER = (
    "id",
    "username",
    "display_name",
    "active",
    "must_change_password",
    "balance_minor",
    "wallet_path",
)


def open_customer_wallet(caller, *, actor_id, username: str, customer_name: str, external_id: str) -> dict:
    """Asks the shop's Pay to open a customer wallet for one of the caller's records. The person approving
    must hold ifpay.customers.manage on that Pay. Asking again for the same record returns the same wallet.
    The answer carries the one-time first password only when the wallet was just opened: show it once, never
    store it."""
    pay, deployment = pay_for(caller)
    user, caps = _member_holding(
        pay,
        actor_id,
        "ifpay.customers.manage",
        "This person may not open IntraForge Pay wallets. Give them the Pay Manager role.",
    )
    external_id = str(external_id or "").strip()
    if not external_id or len(external_id) > MAX_REFERENCE:
        raise ValidationError({"externalId": "Name the record the wallet is for."})
    data = _call(
        deployment,
        "POST",
        "customers",
        {
            "actor": {"id": str(user.pk), "display_name": display_name(user), "capabilities": caps},
            "username": str(username or "customer")[:40],
            "display_name": str(customer_name or "Customer")[:80],
            "source": {
                "app_id": str(caller.id),
                "app_name": _caller_name(caller),
                "external_id": external_id,
            },
        },
    )
    out = {k: data.get(k) for k in _CUSTOMER}
    out["created"] = bool(data.get("created"))
    out["first_password"] = data.get("first_password") if out["created"] else None
    return out


def customer_wallet(caller, wallet_id) -> dict:
    """A wallet the caller opened (username, balance, address); Pay answers 404 for any other."""
    try:
        wid = uuid.UUID(str(wallet_id))
    except ValueError as exc:
        raise NotFound("No such wallet.") from exc
    _, deployment = pay_for(caller, reading=True)
    data = _call(deployment, "GET", f"customers/{wid}?source_app_id={caller.id}")
    return {k: data.get(k) for k in _CUSTOMER}
