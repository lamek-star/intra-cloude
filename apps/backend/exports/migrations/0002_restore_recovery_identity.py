import django.db.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("exports", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="restorejob", name="recovery_version",
            field=models.PositiveSmallIntegerField(default=0), preserve_default=False,
        ),
        migrations.AlterField(
            model_name="restorejob", name="recovery_version",
            field=models.PositiveSmallIntegerField(default=1),
        ),
        migrations.AddField(
            model_name="restorejob", name="source_sha256", field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="restorejob", name="idempotency_key", field=models.UUIDField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="restorejob", name="request_fingerprint",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddConstraint(
            model_name="restorejob",
            constraint=django.db.models.UniqueConstraint(
                fields=("created_by", "idempotency_key"), name="unique_restore_request_per_actor",
            ),
        ),
    ]
