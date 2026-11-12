import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("applications", "0002_applicationcredential_environment"),
    ]

    operations = [
        migrations.CreateModel(
            name="ApiRequestLog",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("method", models.CharField(max_length=8)),
                ("path", models.CharField(max_length=300)),
                ("status", models.PositiveSmallIntegerField()),
                ("duration_ms", models.PositiveIntegerField()),
                ("at", models.DateTimeField(db_index=True)),
                (
                    "application",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="request_log",
                        to="applications.application",
                    ),
                ),
                (
                    "credential",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to="applications.applicationcredential",
                    ),
                ),
            ],
            options={
                "ordering": ["-at", "-id"],
                "indexes": [models.Index(fields=["application", "-at"], name="app_request_log_recent")],
            },
        ),
    ]
