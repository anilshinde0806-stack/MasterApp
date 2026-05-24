# Generated manually for part order header/line split

from django.db import migrations, models
import django.db.models.deletion


def create_headers_for_existing_orders(apps, schema_editor):
    PartOrder = apps.get_model("core", "PartOrder")
    PartOrderHeader = apps.get_model("core", "PartOrderHeader")

    headers_by_key = {}

    for line in PartOrder.objects.select_related("job").all().order_by("job_id", "order_no", "id"):
        key = (
            line.job_id,
            line.order_no or "",
            line.order_date,
            line.supplier or "",
        )

        header = headers_by_key.get(key)

        if header is None:
            header = PartOrderHeader.objects.create(
                job_id=line.job_id,
                order_no=line.order_no or "",
                order_date=line.order_date,
                expected_date=line.expected_date,
                supplier=line.supplier or "",
                status=line.status or "Pending",
                remarks=line.remarks or "",
            )
            headers_by_key[key] = header

        line.order_id = header.id
        line.save(update_fields=["order"])


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0053_partorder"),
    ]

    operations = [
        migrations.CreateModel(
            name="PartOrderHeader",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order_no", models.CharField(blank=True, max_length=50)),
                ("order_date", models.DateField(blank=True, null=True)),
                ("expected_date", models.DateField(blank=True, null=True)),
                ("supplier", models.CharField(blank=True, max_length=150)),
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
                ("remarks", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("job", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="part_order_headers", to="core.jobcard")),
            ],
            options={
                "ordering": ["-updated_at", "-id"],
            },
        ),
        migrations.AddField(
            model_name="partorder",
            name="order",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="lines", to="core.partorderheader"),
        ),
        migrations.AlterField(
            model_name="partorder",
            name="job",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="part_orders", to="core.jobcard"),
        ),
        migrations.RunPython(create_headers_for_existing_orders, migrations.RunPython.noop),
    ]
