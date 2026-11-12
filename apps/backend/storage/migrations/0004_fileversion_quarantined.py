from django.db import migrations, models


def mark_quarantined_history(apps, schema_editor):
    """Versions kept before this field existed: when any upload of the file was ever quarantined, all its
    earlier versions count as quarantined (which one was is not known, so the safe answer for all)."""
    AuditEvent = apps.get_model("audit", "AuditEvent")
    FileVersion = apps.get_model("storage", "FileVersion")
    files = set(
        AuditEvent.objects.filter(
            resource_type="file_object",
            action__in=["storage.file.upload", "storage.file.upload_version"],
            context__quarantined=True,
        ).values_list("resource_id", flat=True)
    )
    if files:
        FileVersion.objects.filter(file_id__in=list(files)).update(quarantined=True)


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0002_auditevent_audit_audit_organiz_353e66_idx"),
        ("storage", "0003_bucket_environment"),
    ]

    operations = [
        migrations.AddField(
            model_name="fileversion",
            name="mime_type",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="fileversion",
            name="quarantined",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(mark_quarantined_history, migrations.RunPython.noop),
    ]
