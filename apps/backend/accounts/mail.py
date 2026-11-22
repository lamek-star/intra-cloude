"""Sending a confirmation link by e-mail (ADR-0026). Optional: without EMAIL_HOST nothing is sent and the caller tells
the administrator to hand the link over. A failure to send never fails the approval itself."""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def enabled() -> bool:
    return bool(settings.EMAIL_HOST)


def send_confirmation(*, to: str, link: str, place: str) -> bool:
    if not enabled():
        return False
    body = (
        f"Your request to work in {place} was approved.\n\n"
        f"Open this link to confirm your email and activate your account (it works once, for 72 hours):\n\n{link}\n\n"
        "If you did not ask for this, ignore this message."
    )
    try:
        send_mail(f"{place}: confirm your account", body, settings.DEFAULT_FROM_EMAIL, [to], fail_silently=False)
    except Exception:  # noqa: BLE001 -- any SMTP failure: the administrator still has the link to hand over
        logger.warning("confirmation e-mail to %s could not be sent", to.split("@")[-1], exc_info=True)
        return False
    return True
