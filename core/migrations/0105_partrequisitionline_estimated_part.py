from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0104_part_requisition_workflow"),
    ]

    operations = [
        migrations.AddField(
            model_name="partrequisitionline",
            name="estimated_part",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="requisition_lines",
                to="core.jobcardpart",
            ),
        ),
    ]
