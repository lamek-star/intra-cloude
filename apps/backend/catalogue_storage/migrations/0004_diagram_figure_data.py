from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalogue_storage", "0003_oempart_applicability_oempart_fitment_notes"),
    ]

    operations = [
        migrations.AddField(
            model_name="diagram",
            name="figure_data",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
