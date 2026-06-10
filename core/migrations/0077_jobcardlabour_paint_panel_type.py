from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0076_jobcardpart_paint_panel_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobcardlabour",
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
