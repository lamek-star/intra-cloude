from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("service_apps", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="serviceapp",
            name="app_type",
            field=models.CharField(
                choices=[("spare_parts", "Spare Parts"), ("intraforge_pay", "IntraForge Pay")], max_length=40
            ),
        ),
    ]
