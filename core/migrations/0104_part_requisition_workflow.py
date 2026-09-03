from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0103_itemdata_inventory_fields_partstocktransaction"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PartRequisition",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("requisition_no", models.CharField(blank=True, max_length=40, unique=True)),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("needed_by", models.DateField(blank=True, null=True)),
                ("priority", models.CharField(choices=[("Normal", "Normal"), ("Urgent", "Urgent"), ("Vehicle Hold", "Vehicle Hold")], default="Normal", max_length=20)),
                ("status", models.CharField(choices=[("Submitted", "Submitted"), ("Partially Fulfilled", "Partially Fulfilled"), ("Fulfilled", "Fulfilled"), ("Cancelled", "Cancelled")], default="Submitted", max_length=30)),
                ("remarks", models.TextField(blank=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="part_requisitions", to="core.jobcard")),
                ("requested_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="part_requisitions_requested", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-requested_at", "-id"]},
        ),
        migrations.CreateModel(
            name="PartRequisitionLine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("requested_qty", models.DecimalField(decimal_places=2, max_digits=12)),
                ("fulfilled_qty", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("remarks", models.CharField(blank=True, max_length=255)),
                ("part", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="requisition_lines", to="core.itemdata")),
                ("requisition", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="core.partrequisition")),
            ],
            options={"ordering": ["id"]},
        ),
        migrations.AddConstraint(
            model_name="partrequisitionline",
            constraint=models.UniqueConstraint(fields=("requisition", "part"), name="unique_part_per_requisition"),
        ),
        migrations.CreateModel(
            name="PartRequisitionFulfillment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity", models.DecimalField(decimal_places=2, max_digits=12)),
                ("issued_at", models.DateTimeField(auto_now_add=True)),
                ("remarks", models.CharField(blank=True, max_length=255)),
                ("issued_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="part_requisition_fulfillments", to=settings.AUTH_USER_MODEL)),
                ("line", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fulfillments", to="core.partrequisitionline")),
                ("stock_transaction", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="requisition_fulfillment", to="core.partstocktransaction")),
            ],
            options={"ordering": ["-issued_at", "-id"]},
        ),
    ]
