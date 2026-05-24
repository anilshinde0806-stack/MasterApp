from django.db import migrations, models
import core.models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0060_jobcard_reinspection"),
    ]

    operations = [
        migrations.AlterField(
            model_name="jobcardreinspectionphoto",
            name="image",
            field=models.ImageField(upload_to=core.models.reinspection_photo_upload_path),
        ),
    ]
