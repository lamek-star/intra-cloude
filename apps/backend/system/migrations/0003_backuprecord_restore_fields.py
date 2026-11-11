from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('system', '0002_alter_backuprecord_backup_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='backuprecord',
            name='restored_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='backuprecord',
            name='restore_error',
            field=models.TextField(blank=True),
        ),
    ]
