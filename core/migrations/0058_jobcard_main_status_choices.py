from django.db import migrations, models


def normalize_jobcard_main_status(apps, schema_editor):
    JobCard = apps.get_model("core", "JobCard")

    JobCard.objects.filter(
        repair_status__in=[
            "Pending",
            "Started",
            "Under Repair",
            "Paint",
            "Assembly",
            "QC",
        ]
    ).update(repair_status="Open")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0057_workallocation_save_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="jobcard",
            name="repair_status",
            field=models.CharField(
                choices=[
                    ("Open", "Open"),
                    ("Completed", "Completed"),
                    ("Closed", "Closed"),
                    ("Cancellation", "Cancellation"),
                ],
                default="Open",
                max_length=30,
            ),
        ),
        migrations.RunPython(
            normalize_jobcard_main_status,
            migrations.RunPython.noop,
        ),
    ]
