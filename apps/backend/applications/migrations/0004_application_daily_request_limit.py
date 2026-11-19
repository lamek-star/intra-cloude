from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("applications", "0003_apirequestlog"),
    ]

    operations = [
        migrations.AddField(
            model_name="application",
            name="daily_request_limit",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
