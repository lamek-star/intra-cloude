import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_passkey_only_db_default"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="must_change_password",
            # A database default too: a failed upgrade rolls back to the previous release, which inserts users
            # without this column (as for passkey_only, 0004).
            field=models.BooleanField(default=False, db_default=False),
        ),
        migrations.CreateModel(
            name="MFARecoveryCode",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("code_hash", models.CharField(max_length=64)),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mfa_recovery_codes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
