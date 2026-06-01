from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0072_jobcardadditionalapprovalphoto"),
    ]

    operations = [
        migrations.AddField(
            model_name="workallocationpart",
            name="advisor_approval_status",
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
            model_name="workallocationpart",
            name="is_additional",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="workallocationlabour",
            name="advisor_approval_status",
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
            model_name="workallocationlabour",
            name="is_additional",
            field=models.BooleanField(default=False),
        ),
    ]
