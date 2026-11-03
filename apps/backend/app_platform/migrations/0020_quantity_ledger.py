import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("app_platform", "0019_durable_delivery_schedule"),
    ]

    operations = [
        migrations.CreateModel(
            name="QuantityLedgerBinding",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("allow_negative", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "balance_field",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="app_platform.fielddefinition",
                    ),
                ),
                (
                    "balance_model",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="app_platform.modeldefinition",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL
                    ),
                ),
                (
                    "instance",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="quantity_ledgers",
                        to="app_platform.appinstance",
                    ),
                ),
                (
                    "movement_field",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="app_platform.fielddefinition",
                    ),
                ),
                (
                    "movement_model",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="app_platform.modeldefinition",
                    ),
                ),
                (
                    "unique_constraint",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="app_platform.constraintdefinition",
                    ),
                ),
            ],
            options={"ordering": ["created_at", "id"]},
        ),
        migrations.AddConstraint(
            model_name="quantityledgerbinding",
            constraint=models.UniqueConstraint(
                fields=("balance_model", "balance_field"), name="app_ledger_balance_unique"
            ),
        ),
        migrations.AddConstraint(
            model_name="quantityledgerbinding",
            constraint=models.UniqueConstraint(
                fields=("movement_model", "movement_field"), name="app_ledger_movement_unique"
            ),
        ),
        migrations.CreateModel(
            name="QuantityLedgerDimension",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "balance_relationship",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="app_platform.relationshipdefinition",
                    ),
                ),
                (
                    "binding",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dimensions",
                        to="app_platform.quantityledgerbinding",
                    ),
                ),
                (
                    "movement_relationship",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="app_platform.relationshipdefinition",
                    ),
                ),
            ],
            options={"ordering": ["id"]},
        ),
        migrations.AddConstraint(
            model_name="quantityledgerdimension",
            constraint=models.UniqueConstraint(
                fields=("binding", "balance_relationship"), name="app_ledger_dim_balance_unique"
            ),
        ),
        migrations.AddConstraint(
            model_name="quantityledgerdimension",
            constraint=models.UniqueConstraint(
                fields=("binding", "movement_relationship"), name="app_ledger_dim_movement_unique"
            ),
        ),
    ]
