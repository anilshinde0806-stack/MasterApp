from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0058_jobcard_main_status_choices"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="jobcard",
            name="part_order_status",
        ),
    ]
