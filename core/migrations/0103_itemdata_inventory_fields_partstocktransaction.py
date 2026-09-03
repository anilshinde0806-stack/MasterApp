from decimal import Decimal

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0102_alter_employee_employee_type"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="itemdata",
            name="bin_location",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="itemdata",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name="itemdata",
            name="current_stock",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="itemdata",
            name="gst_percent",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name="itemdata",
            name="hsn_code",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="itemdata",
            name="manufacturer",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="itemdata",
            name="preferred_supplier",
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name="itemdata",
            name="reorder_level",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="itemdata",
            name="unit",
            field=models.CharField(
                choices=[
                    ("Nos", "Nos"),
                    ("Set", "Set"),
                    ("Pair", "Pair"),
                    ("Litre", "Litre"),
                    ("Kg", "Kg"),
                    ("Metre", "Metre"),
                ],
                default="Nos",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="itemdata",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.CreateModel(
            name="PartStockTransaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("transaction_type", models.CharField(choices=[("Opening", "Opening Stock"), ("Receipt", "Stock Receipt"), ("Issue", "Stock Issue"), ("Return", "Stock Return"), ("Adjustment", "Stock Adjustment")], default="Adjustment", max_length=20)),
                ("quantity_change", models.DecimalField(decimal_places=2, max_digits=12)),
                ("balance_after", models.DecimalField(decimal_places=2, max_digits=12)),
                ("reference", models.CharField(blank=True, max_length=100)),
                ("remarks", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="part_stock_transactions", to=settings.AUTH_USER_MODEL)),
                ("part", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="stock_transactions", to="core.itemdata")),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
    ]
