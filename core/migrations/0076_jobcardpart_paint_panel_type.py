from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0075_workflow_datetime_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobcardpart",
            name="paint_panel_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "No Paint Panel"),
                    ("New", "New Panel Painting"),
                    ("Repair", "Repair Panel Painting"),
                ],
                default="",
                max_length=20,
            ),
        ),
    ]
