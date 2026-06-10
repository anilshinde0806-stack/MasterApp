from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0077_jobcardlabour_paint_panel_type"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="jobcardpart",
            name="paint_panel_type",
        ),
    ]
