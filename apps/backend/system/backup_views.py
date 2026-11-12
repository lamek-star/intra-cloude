"""The Backups page (Super Administrator only, system.admin): every backup of this installation, whether its
restore test passed, and "Back up now". Restoring replaces live data, so it stays in the Control Center on the
shop PC (docs/operations/BACKUP_RESTORE.md); nothing here restores.
"""

import os
from datetime import timedelta

from django.utils import timezone
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit import services as audit
from permissions.services import has_permission

from .models import BackupRecord

# A backup of one type still running after this long is taken as stuck, so a new one may start.
STUCK_AFTER = timedelta(hours=2)


def _record_json(r: BackupRecord) -> dict:
    return {
        "id": str(r.id),
        "type": r.backup_type,
        "type_label": r.get_backup_type_display(),
        "status": r.status,
        # The file's name only: where it sits on the server is not the browser's business.
        "file_name": os.path.basename(r.file_path) if r.file_path else "",
        "size_bytes": r.size_bytes,
        "error": r.error_message[:500],
        "started_at": r.started_at.isoformat(),
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        "verified_restorable": r.verified_restorable,
        "verified_at": r.verified_at.isoformat() if r.verified_at else None,
        "verification_error": r.verification_error[:500],
        "restored_at": r.restored_at.isoformat() if r.restored_at else None,
    }


class _AdminOnly(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.is_admin = has_permission(request.user, "system.admin", organization_id=None)


class BackupListView(_AdminOnly):
    def get(self, request):
        if not self.is_admin:
            return Response(
                {"detail": "Only the Super Administrator can see this installation's backups."}, status=403
            )
        records = list(BackupRecord.objects.all()[:60])
        latest = {}
        for t in BackupRecord.BackupType.values:
            ok = BackupRecord.objects.filter(backup_type=t, status=BackupRecord.Status.SUCCESS).first()
            latest[t] = {
                "label": BackupRecord.BackupType(t).label,
                "last_success": ok.completed_at.isoformat() if ok and ok.completed_at else None,
                "verified": bool(ok and ok.verified_restorable),
            }
        return Response({"latest": latest, "backups": [_record_json(r) for r in records]})


class BackupRunView(_AdminOnly):
    def post(self, request):
        from .tasks import run_backup_task

        if not self.is_admin:
            return Response({"detail": "Only the Super Administrator can start a backup."}, status=403)
        data = request.data if isinstance(request.data, dict) else {}
        wanted = data.get("type", "all")
        types = BackupRecord.BackupType.values if wanted == "all" else [wanted]
        if any(t not in BackupRecord.BackupType.values for t in types):
            return Response({"type": "Unknown backup type."}, status=400)
        busy = set(
            BackupRecord.objects.filter(
                backup_type__in=types,
                status=BackupRecord.Status.RUNNING,
                started_at__gte=timezone.now() - STUCK_AFTER,
            ).values_list("backup_type", flat=True)
        )
        started = [t for t in types if t not in busy]
        for t in started:
            run_backup_task.delay(t)
        audit.record(
            actor=request.user,
            organization_id=None,
            action="system.backup.request",
            resource_type="backup",
            context={"types": started, "already_running": sorted(busy)},
        )
        return Response({"started": started, "already_running": sorted(busy)}, status=202)


class HealthView(_AdminOnly):
    """Health history and alerts for this installation (Super Administrator only)."""

    def get(self, request):
        from . import health

        if not self.is_admin:
            return Response(
                {"detail": "Only the Super Administrator can see this installation's health."}, status=403
            )
        return Response(health.summary())
