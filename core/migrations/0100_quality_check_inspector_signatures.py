from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0099_quality_check_evidence_signature"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="QualityCheckInspectorSignature",
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
                        upload_to="quality_check/signatures/",
                    ),
                ),
                ("signed_at", models.DateTimeField(auto_now_add=True)),
                (
                    "inspector",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="quality_check_signatures",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "quality_check",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="inspector_signatures",
                        to="core.jobcardqualitycheck",
                    ),
                ),
            ],
            options={"ordering": ["signed_at", "id"]},
        ),
    ]
