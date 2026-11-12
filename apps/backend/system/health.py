"""Health history and alerts. Every 5 minutes (Celery Beat) the checks run and are kept HEALTH_HISTORY_DAYS
days; a check failing twice in a row opens an alert, which closes by itself when the check passes again.
Besides the dependencies /readyz checks, two things a shop would otherwise notice too late: the last good
backup is older than a day and a half, and the backups' disk is nearly full. When no sample has been taken for
15 minutes the background jobs themselves have stopped, which no sample can say, so that is worked out when
the page is read."""

import shutil
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import BackupRecord, HealthAlert, HealthSample

LABELS = {
    "database:default": "IntraForge's database",
    "database:tenant": "The business data database",
    "valkey": "The job queue (Valkey)",
    "object_storage": "File storage",
    "backups": "Recent backup",
    "disk": "Free space for backups",
    "jobs": "Background jobs",
}
STALE_AFTER = timedelta(minutes=15)
BACKUP_MAX_AGE = timedelta(hours=36)


def _backup_check(now) -> tuple[bool, str]:
    last = (
        BackupRecord.objects.filter(status=BackupRecord.Status.SUCCESS, completed_at__isnull=False)
        .order_by("-completed_at")
        .first()
    )
    if last is None:
        return False, "No backup has finished yet."
    if now - last.completed_at > BACKUP_MAX_AGE:
        return False, f"The last good backup finished {last.completed_at:%Y-%m-%d %H:%M} UTC."
    return True, ""


def _disk_check() -> tuple[bool, str]:
    try:
        usage = shutil.disk_usage(settings.BACKUP_DIR)
    except OSError:
        return True, ""  # no backup folder in this deployment: nothing to watch
    free_gb = usage.free / 1024**3
    if usage.free < usage.total * 0.05 or free_gb < 2:
        return False, f"Only {free_gb:.1f} GB free where backups are kept."
    return True, ""


def run_checks(now=None) -> dict[str, tuple[bool, str]]:
    from .views import _dependency_checks

    now = now or timezone.now()
    deps, _ = _dependency_checks()
    out = {name: (up, "" if up else "Not reachable.") for name, up in deps.items()}
    out["backups"] = _backup_check(now)
    out["disk"] = _disk_check()
    return out


def record(now=None) -> HealthSample:
    """Takes one sample, opens and closes alerts, and drops samples older than HEALTH_HISTORY_DAYS."""
    now = now or timezone.now()
    results = run_checks(now)
    with transaction.atomic():
        previous = HealthSample.objects.order_by("-at").first()
        sample = HealthSample.objects.create(at=now, checks={k: ok for k, (ok, _d) in results.items()})
        open_alerts = {
            a.check_name: a for a in HealthAlert.objects.select_for_update().filter(closed_at__isnull=True)
        }
        for check, (ok, detail) in results.items():
            alert = open_alerts.get(check)
            if ok and alert:
                alert.closed_at = now
                alert.save(update_fields=["closed_at"])
            elif not ok and alert is None and previous is not None and previous.checks.get(check) is False:
                HealthAlert.objects.create(check_name=check, detail=detail[:300], opened_at=now)
            elif not ok and alert is not None and detail and alert.detail != detail[:300]:
                alert.detail = detail[:300]
                alert.save(update_fields=["detail"])
        # A sample was taken, so background jobs run again: close a "jobs" alert left from a stop.
        HealthAlert.objects.filter(check_name="jobs", closed_at__isnull=True).update(closed_at=now)
    HealthSample.objects.filter(at__lt=now - timedelta(days=settings.HEALTH_HISTORY_DAYS)).delete()
    return sample


def summary(now=None) -> dict:
    """For the Health page: the latest result of each check, the last 24 hours by hour, and the alerts."""
    now = now or timezone.now()
    latest = HealthSample.objects.order_by("-at").first()
    since = now - timedelta(hours=24)
    hours: dict[str, list[dict]] = {}
    for sample in HealthSample.objects.filter(at__gte=since).order_by("at"):
        hour = sample.at.replace(minute=0, second=0, microsecond=0).isoformat()
        for check, ok in sample.checks.items():
            row = hours.setdefault(check, [])
            if not row or row[-1]["hour"] != hour:
                row.append({"hour": hour, "ok": 0, "failed": 0})
            row[-1]["ok" if ok else "failed"] += 1
    alerts = [
        {
            "check": a.check_name,
            "label": LABELS.get(a.check_name, a.check_name),
            "detail": a.detail,
            "opened_at": a.opened_at.isoformat(),
            "closed_at": a.closed_at.isoformat() if a.closed_at else None,
        }
        for a in HealthAlert.objects.filter(
            opened_at__gte=now - timedelta(days=settings.HEALTH_HISTORY_DAYS)
        )[:50]
    ]
    if latest is None or now - latest.at > STALE_AFTER:
        alerts.insert(
            0,
            {
                "check": "jobs",
                "label": LABELS["jobs"],
                "detail": "No health check has run since "
                + (f"{latest.at:%Y-%m-%d %H:%M} UTC" if latest else "IntraForge started")
                + ": the background jobs (worker or scheduler) are not running,"
                " so backups do not run either.",
                "opened_at": (latest.at if latest else now).isoformat(),
                "closed_at": None,
            },
        )
    return {
        "latest": {
            "at": latest.at.isoformat() if latest else None,
            "checks": [
                {"check": k, "label": LABELS.get(k, k), "ok": v}
                for k, v in (latest.checks.items() if latest else [])
            ],
        },
        "hours": [{"check": k, "label": LABELS.get(k, k), "hours": v} for k, v in hours.items()],
        "alerts": alerts,
        "open_alerts": sum(1 for a in alerts if a["closed_at"] is None),
    }
