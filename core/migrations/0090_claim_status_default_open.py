from django.db import migrations, models


def normalize_created_status(apps, schema_editor):
    Claim = apps.get_model("core", "Claim")
    Claim.objects.filter(status="Created").update(status="Open")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0089_direct_jobcard_vehicle_branch"),
    ]

    operations = [
        migrations.AlterField(
            model_name="claim",
            name="status",
            field=models.CharField(
                choices=[
                    ("Open", "Open"),
                    ("Closed", "Closed"),
                    ("Cancelled", "Cancelled"),
                ],
                default="Open",
                max_length=30,
            ),
        ),
        migrations.RunPython(normalize_created_status, migrations.RunPython.noop),
    ]
