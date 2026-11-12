from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("system", "0003_backuprecord_restore_fields")]

    operations = [
        migrations.CreateModel(
            name="HealthSample",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("at", models.DateTimeField(db_index=True)),
                ("checks", models.JSONField(default=dict)),
            ],
            options={"ordering": ["-at"]},
        ),
        migrations.CreateModel(
            name="HealthAlert",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("check_name", models.CharField(max_length=60)),
                ("detail", models.CharField(blank=True, max_length=300)),
                ("opened_at", models.DateTimeField()),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"ordering": ["-opened_at"]},
        ),
    ]
