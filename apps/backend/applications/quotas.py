"""Per-application daily request limit (Application.daily_request_limit; empty = no limit).

Enforced where an application's bearer credential is accepted (applications/authentication.py), so it covers
every endpoint the credential can reach -- also the ones with their own throttle_classes (uploads, imports), which
DRF's default throttles never see. The count is one shared counter per application per day in the cache (Valkey,
CACHES in settings: shared by every gunicorn worker), so three workers cannot each allow the full limit.

A day is IntraForge's day (settings.TIME_ZONE); the counter expires by itself two days later. If the cache cannot
be reached the request is allowed and a warning is logged: the limit protects the shop's resources, it is not an
access rule (permissions and grants still decide what the credential may do).
"""

import datetime
import logging

from django.core.cache import cache
from django.utils import timezone
from rest_framework.exceptions import Throttled

logger = logging.getLogger(__name__)

MAX_LIMIT = 10_000_000
_TTL_SECONDS = 2 * 24 * 3600


def _key(application_id, day: datetime.date) -> str:
    return f"app-quota:{application_id}:{day.isoformat()}"


def seconds_until_tomorrow(now=None) -> int:
    now = timezone.localtime(now or timezone.now())
    tomorrow = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(1, int((tomorrow - now).total_seconds()))


def used_today(application_id) -> int:
    """Requests counted so far today (0 when nothing was counted or the cache is not reachable)."""
    try:
        return int(cache.get(_key(application_id, timezone.localdate())) or 0)
    except Exception:  # noqa: BLE001 - a display value; never fail a page over it
        logger.warning("could not read an application's request count", exc_info=True)
        return 0


class DailyLimitReached(Throttled):
    default_code = "daily_limit_reached"


def count_and_check(application_id, limit) -> None:
    """Counts one request of the application and refuses it (429, Retry-After until midnight) once the day's
    count is over the limit. Every request is counted, so a limit set in the middle of the day starts from what
    was already used."""
    key = _key(application_id, timezone.localdate())
    try:
        cache.add(key, 0, timeout=_TTL_SECONDS)
        used = cache.incr(key)
    except Exception:  # noqa: BLE001 - see the module docstring: allow, and say so in the log
        logger.warning("could not count an application's request; the daily limit was not checked", exc_info=True)
        return
    if limit is not None and used > limit:
        raise DailyLimitReached(
            wait=seconds_until_tomorrow(),
            detail=(
                f"This application has made all {limit} requests it may make today. It can make requests again "
                "tomorrow. The owner can change the limit on the application's page in IntraForge."
            ),
        )
