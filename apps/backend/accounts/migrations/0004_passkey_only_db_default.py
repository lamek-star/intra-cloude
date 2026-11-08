from django.db import migrations, models


class Migration(migrations.Migration):
    """A database default for passkey_only: an upgrade that fails rolls back to the previous release, which runs on
    this migrated data and inserts users without the column."""

    dependencies = [("accounts", "0003_passkeys")]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="passkey_only",
            field=models.BooleanField(default=False, db_default=False),
        ),
    ]
