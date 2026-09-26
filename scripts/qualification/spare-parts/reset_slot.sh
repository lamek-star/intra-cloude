#!/usr/bin/env bash
# DISPOSABLE QUALIFICATION STACK ONLY -- never run against a real installation: empty the Spare Parts deployment slot (drops the disposable test install's schema and files).
docker exec intraforge-local-qualification-backend-1 python manage.py shell -c "
from service_apps.models import ServiceApp
from service_apps import provisioning
for a in ServiceApp.objects.all():
    provisioning.drop_schema(a.schema_name)
    b=a.bucket; a.sessions.all().delete(); a.audit_receipts.all().delete(); a.delete(); b.files.all().delete(); b.folders.all().delete(); b.delete()
    print('reset', a.schema_name)
" 2>&1 | tail -2
docker restart intraforge-local-qualification-spareparts-1 >/dev/null && sleep 8
