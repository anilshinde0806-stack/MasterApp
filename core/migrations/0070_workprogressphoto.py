from django.db import migrations, models
import django.db.models.deletion
import core.models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0069_claim_self_survey"),
    ]

    operations = [
        migrations.CreateModel(
            name="WorkProgressPhoto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to=core.models.work_progress_photo_upload_path)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("progress", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="photos", to="core.workprogress")),
            ],
        ),
    ]
