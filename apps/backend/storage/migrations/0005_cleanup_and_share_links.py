import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("storage", "0004_fileversion_quarantined"),
    ]

    operations = [
        migrations.AddField(
            model_name="bucket",
            name="trash_days",
            field=models.PositiveIntegerField(db_default=30, default=30),
        ),
        migrations.AddField(
            model_name="bucket",
            name="version_days",
            field=models.PositiveIntegerField(db_default=0, default=0),
        ),
        migrations.CreateModel(
            name="FileShareLink",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("token_hash", models.CharField(max_length=64, unique=True)),
                ("expires_at", models.DateTimeField()),
                ("max_downloads", models.PositiveIntegerField(blank=True, null=True)),
                ("downloads", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="share_links_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "file",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="share_links",
                        to="storage.fileobject",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
