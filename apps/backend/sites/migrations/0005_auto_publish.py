from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("hosted_sites", "0004_internet_gate")]

    operations = [
        migrations.AddField(
            model_name="site",
            name="internet_auto",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="internetgateway",
            name="auto_domain",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
    ]
