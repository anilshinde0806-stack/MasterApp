from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0070_workprogressphoto"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobcard",
            name="additional_approval_required",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="jobcard",
            name="second_approval_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Not Required"),
                    ("Pending", "Pending"),
                    ("Approved", "Approved"),
                    ("Rejected", "Rejected"),
                ],
                default="",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="jobcard",
            name="additional_approval_reason",
            field=models.TextField(blank=True),
        ),
    ]
