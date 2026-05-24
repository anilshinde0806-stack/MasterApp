from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0061_reinspection_photo_claim_folder"),
    ]

    operations = [
        migrations.AddField(
            model_name="workallocation",
            name="part_entry_complete",
            field=models.BooleanField(default=False),
        ),
    ]
