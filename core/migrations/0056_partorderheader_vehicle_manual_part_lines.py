from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0055_alter_partorder_part"),
    ]

    operations = [
        migrations.AddField(
            model_name="partorderheader",
            name="vehicle",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="part_order_headers",
                to="core.vehicle",
            ),
        ),
        migrations.AddField(
            model_name="partorder",
            name="manual_description",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="partorder",
            name="manual_part_no",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name="partorder",
            name="part",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="part_orders",
                to="core.jobcardpart",
            ),
        ),
    ]
