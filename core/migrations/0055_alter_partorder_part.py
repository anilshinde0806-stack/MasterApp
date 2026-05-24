from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0054_partorderheader_partorder_order_nullable_job"),
    ]

    operations = [
        migrations.AlterField(
            model_name="partorder",
            name="part",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="part_orders",
                to="core.jobcardpart",
            ),
        ),
    ]
