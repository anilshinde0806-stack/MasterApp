from django.db import migrations, models
import django.db.models.deletion
import core.models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0071_jobcard_additional_approval"),
    ]

    operations = [
        migrations.CreateModel(
            name="JobCardAdditionalApprovalPhoto",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "image",
                    models.ImageField(
                        upload_to=core.models.additional_approval_photo_upload_path
                    ),
                ),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "job",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="additional_approval_photos",
                        to="core.jobcard",
                    ),
                ),
            ],
        ),
    ]
