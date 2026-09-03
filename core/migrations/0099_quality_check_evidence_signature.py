from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0098_qualitycheckitem"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="jobcardqualitycheck",
            name="inspector_signature",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="quality_check/signatures/",
            ),
        ),
        migrations.CreateModel(
            name="QualityCheckEvidencePhoto",
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
                        upload_to="quality_check/evidence/%Y/%m/",
                    ),
                ),
                (
                    "caption",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=200,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "quality_check",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="evidence_photos",
                        to="core.jobcardqualitycheck",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="quality_check_evidence_uploaded",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["created_at", "id"]},
        ),
    ]
