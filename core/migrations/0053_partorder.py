# Generated manually for part order tracking

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0052_jobcardassessmentlabour_deduction_percent"),
    ]

    operations = [
        migrations.CreateModel(
            name="PartOrder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order_no", models.CharField(blank=True, max_length=50)),
                ("supplier", models.CharField(blank=True, max_length=150)),
                ("order_date", models.DateField(blank=True, null=True)),
                ("expected_date", models.DateField(blank=True, null=True)),
                ("received_date", models.DateField(blank=True, null=True)),
                ("ordered_qty", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("received_qty", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("Pending", "Pending"),
                            ("Order Placed", "Order Placed"),
                            ("In Transit", "In Transit"),
                            ("Partially Received", "Partially Received"),
                            ("Received", "Received"),
                            ("Back Order", "Back Order"),
                            ("Cancelled", "Cancelled"),
                        ],
                        default="Pending",
                        max_length=30,
                    ),
                ),
                ("tracking_ref", models.CharField(blank=True, max_length=100)),
                ("remarks", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="part_orders", to="core.jobcard")),
                ("part", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="part_order", to="core.jobcardpart")),
            ],
            options={
                "ordering": ["-updated_at", "-id"],
            },
        ),
    ]
