from django.db import migrations, models


class Migration(migrations.Migration):
    """Database defaults for the auto-publish columns: an upgrade that fails rolls back to the previous release, which
    runs on this migrated data and inserts sites and the gateway without them."""

    dependencies = [("hosted_sites", "0005_auto_publish")]

    operations = [
        migrations.AlterField(
            model_name="site",
            name="internet_auto",
            field=models.BooleanField(default=False, db_default=False),
        ),
        migrations.AlterField(
            model_name="internetgateway",
            name="auto_domain",
            field=models.CharField(blank=True, default="", db_default="", max_length=200),
        ),
    ]
