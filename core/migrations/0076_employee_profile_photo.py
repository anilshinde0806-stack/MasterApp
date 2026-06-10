from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0075_workflow_datetime_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="employee",
            name="profile_photo",
            field=models.ImageField(blank=True, null=True, upload_to="employee_profile_photos/"),
        ),
    ]
