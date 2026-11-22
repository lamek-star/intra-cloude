"""
Access requests (ADR-0026): someone asks, from an installed application's Request access page, to work in an
organization; an administrator approves (choosing the role) or rejects; a new account is then confirmed by a
single-use link (accounts/links.py).

Every rule lives here so the IntraForge pages and the applications (through the internal service API) share it:
approving needs users.manage AND permissions.manage in that organization, the role is the administrator's choice
(the requested one is only a suggestion), and roles are given through permissions.services.assign_role.
"""

from __future__ import annotations

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts import links, mail
from accounts.models import User
from audit import services as audit
from audit.models import AuditEvent
from permissions.catalog import ORGANIZATION_ROLE_SUMMARIES, SYSTEM_ROLES
from permissions.models import RoleAssignment
from permissions.services import PermissionError_, assign_role, has_permission
from system import features

from .models import AccessRequest, Membership

# An application's own roles: the ones a person may ask for from its Request access page.
APP_ROLE_PREFIX = {"spare_parts": "spare-parts-", "intraforge_pay": "pay-", "pharmacy": "pharmacy-"}
SAME_ANSWER = (
    "Thank you. If the details are right, your request is now with the shop's administrator. "
    "Once it is approved you receive a link to activate your account."
)


class AccessError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def requestable_roles(app) -> list[dict]:
    prefix = APP_ROLE_PREFIX.get(app.app_type)
    if not prefix:
        return []
    return [
        {"slug": slug, "name": SYSTEM_ROLES[slug][0], "summary": summary}
        for slug, summary in ORGANIZATION_ROLE_SUMMARIES.items()
        if slug.startswith(prefix)
    ]


def _check_requested_role(app, role) -> str:
    role = role.strip() if isinstance(role, str) else ""
    if role and role not in {r["slug"] for r in requestable_roles(app)}:
        raise AccessError("Choose one of this app's jobs.")
    return role


def _text(value, limit: int) -> str:
    return value.strip()[:limit] if isinstance(value, str) else ""


def can_decide(user, organization) -> bool:
    return has_permission(user, "users.manage", organization_id=organization.id) and has_permission(
        user, "permissions.manage", organization_id=organization.id
    )


def request_as_new_person(*, app, data: dict) -> str:
    """A person with no account asks for access. Always the same answer (SAME_ANSWER), whether or not the email
    already has an account, so this page cannot tell anyone who works here."""
    if not features.may_request_access():
        raise AccessError("This shop does not take requests from here. Ask the shop's administrator.", 403)
    email = User.objects.normalize_email(_text(data.get("email"), 254))
    if "@" not in email:
        raise AccessError("Enter your email address.")
    role = _check_requested_role(app, data.get("requested_role"))
    password = data.get("password") if isinstance(data.get("password"), str) else ""
    candidate = User(email=email, first_name=_text(data.get("first_name"), 150))
    try:
        password_validation.validate_password(password, candidate)
    except ValidationError as exc:
        raise AccessError(" ".join(exc.messages)) from exc
    if User.objects.filter(email__iexact=email).exists():
        audit.record(
            actor=None,
            organization_id=app.organization_id,
            action="organization.access_request.create",
            resource_type="service_app",
            resource_id=app.id,
            result=AuditEvent.Result.DENIED,
            context={"reason": "an account with this email exists; it must sign in to ask"},
        )
        return SAME_ANSWER
    with transaction.atomic():
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=_text(data.get("first_name"), 150),
            last_name=_text(data.get("last_name"), 150),
        )
        user.phone = _text(data.get("phone"), 40)
        user.is_active = False
        user.save(update_fields=["phone", "is_active"])
        request = AccessRequest.objects.create(
            organization_id=app.organization_id,
            service_app=app,
            user=user,
            requested_role=role,
            message=_text(data.get("message"), 500),
            new_account=True,
        )
        audit.record(
            actor=None,
            organization_id=app.organization_id,
            action="organization.access_request.create",
            resource_type="access_request",
            resource_id=request.id,
            context={"app": str(app.id), "requested_role": role, "new_account": True},
        )
    return SAME_ANSWER


def request_as_member(*, user, app, data: dict) -> AccessRequest:
    """Someone signed in asks for access to an app (no second account is made)."""
    if not features.may_request_access():
        raise AccessError("This shop does not take requests from here. Ask the shop's administrator.", 403)
    role = _check_requested_role(app, data.get("requested_role"))
    prefix = APP_ROLE_PREFIX.get(app.app_type, "\0")
    if RoleAssignment.objects.filter(
        user=user, organization_id=app.organization_id, role__slug__startswith=prefix
    ).exists():
        raise AccessError("You can already work in this app.", 409)
    pending = {"user": user, "organization_id": app.organization_id, "service_app": app}
    existing = AccessRequest.objects.filter(**pending, status=AccessRequest.Status.PENDING).first()
    if existing:
        return existing
    try:
        with transaction.atomic():
            request = AccessRequest.objects.create(
                **pending, requested_role=role, message=_text(data.get("message"), 500)
            )
    except IntegrityError:
        return AccessRequest.objects.get(**pending, status=AccessRequest.Status.PENDING)
    audit.record(
        actor=user,
        organization_id=app.organization_id,
        action="organization.access_request.create",
        resource_type="access_request",
        resource_id=request.id,
        context={"app": str(app.id), "requested_role": role, "new_account": False},
    )
    return request


def _place(request: AccessRequest) -> str:
    if request.service_app_id:
        app = request.service_app
        return (app.config or {}).get("shopName") or app.display_name
    return request.organization.name


def _link_for(request: AccessRequest, actor, base_url: str) -> dict:
    token = links.issue(user=request.user, created_by=actor, organization_id=request.organization_id)
    link = links.url(base_url, token)
    emailed = mail.send_confirmation(to=request.user.email, link=link, place=_place(request))
    return {"link": link, "emailed": emailed}


def _locked(request_id, organization) -> AccessRequest:
    request = (
        AccessRequest.objects.select_for_update(of=("self",))
        .select_related("user", "service_app", "organization")
        .filter(pk=request_id, organization=organization)
        .first()
    )
    if request is None:
        raise AccessError("No such request.", 404)
    if request.status != AccessRequest.Status.PENDING:
        raise AccessError("This request was already decided.", 409)
    return request


def approve(*, request_id, organization, actor, role_slug, note, base_url: str) -> dict:
    if not can_decide(actor, organization):
        raise AccessError("You may not approve requests in this organization.", 403)
    role_slug = role_slug.strip() if isinstance(role_slug, str) else ""
    if role_slug not in ORGANIZATION_ROLE_SUMMARIES:
        raise AccessError("Choose the role to give.")
    with transaction.atomic():
        request = _locked(request_id, organization)
        Membership.objects.get_or_create(
            user=request.user,
            organization=organization,
            defaults={"status": Membership.Status.ACTIVE, "invited_by": actor},
        )
        if not RoleAssignment.objects.filter(
            user=request.user, organization=organization, role__slug=role_slug, role__organization__isnull=True
        ).exists():
            try:
                assign_role(user=request.user, role_slug=role_slug, organization=organization, granted_by=actor)
            except PermissionError_ as exc:
                raise AccessError(str(exc)) from exc
        request.status = AccessRequest.Status.APPROVED
        request.granted_role = role_slug
        request.decision_note = _text(note, 500)
        request.decided_by = actor
        request.decided_at = timezone.now()
        request.save(update_fields=["status", "granted_role", "decision_note", "decided_by", "decided_at"])
        audit.record(
            actor=actor,
            organization_id=organization.id,
            action="organization.access_request.approve",
            resource_type="access_request",
            resource_id=request.id,
            context={"role": role_slug, "requested_role": request.requested_role},
        )
    result = {"request": describe(request), "link": None, "emailed": False}
    if request.new_account and not request.user.is_active:
        result.update(_link_for(request, actor, base_url))
    return result


def reject(*, request_id, organization, actor, note) -> dict:
    if not can_decide(actor, organization):
        raise AccessError("You may not decide requests in this organization.", 403)
    with transaction.atomic():
        request = _locked(request_id, organization)
        request.status = AccessRequest.Status.REJECTED
        request.decision_note = _text(note, 500)
        request.decided_by = actor
        request.decided_at = timezone.now()
        request.save(update_fields=["status", "decision_note", "decided_by", "decided_at"])
        audit.record(
            actor=actor,
            organization_id=organization.id,
            action="organization.access_request.reject",
            resource_type="access_request",
            resource_id=request.id,
        )
    return {"request": describe(request)}


def new_link(*, request_id, organization, actor, base_url: str) -> dict:
    """A fresh confirmation link for an approved new account that has not activated yet (the old one ends)."""
    if not can_decide(actor, organization):
        raise AccessError("You may not do this in this organization.", 403)
    request = (
        AccessRequest.objects.select_related("user", "service_app", "organization")
        .filter(pk=request_id, organization=organization)
        .first()
    )
    if request is None:
        raise AccessError("No such request.", 404)
    if request.status != AccessRequest.Status.APPROVED or not request.new_account or request.user.is_active:
        raise AccessError("Only an approved account that is not activated yet gets a new link.", 409)
    return _link_for(request, actor, base_url)


def describe(request: AccessRequest) -> dict:
    user = request.user
    app = request.service_app
    return {
        "id": str(request.id),
        "status": request.status,
        "email": user.email,
        "name": user.get_full_name(),
        "phone": user.phone,
        "app": {"id": str(app.id), "name": _place(request), "type": app.app_type} if app else None,
        "requested_role": request.requested_role,
        "requested_role_name": SYSTEM_ROLES[request.requested_role][0]
        if request.requested_role in SYSTEM_ROLES
        else "",
        "granted_role": request.granted_role,
        "message": request.message,
        "new_account": request.new_account,
        "activated": user.is_active,
        "decision_note": request.decision_note,
        "decided_by": request.decided_by.email if request.decided_by_id else None,
        "decided_at": request.decided_at.isoformat() if request.decided_at else None,
        "created_at": request.created_at.isoformat(),
    }


def for_organization(organization, *, status: str | None = None, app=None):
    qs = AccessRequest.objects.filter(organization=organization).select_related(
        "user", "service_app", "decided_by", "organization"
    )
    if status in AccessRequest.Status.values:
        qs = qs.filter(status=status)
    if app is not None:
        qs = qs.filter(service_app=app)
    return qs
