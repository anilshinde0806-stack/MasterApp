from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0059_remove_jobcard_part_order_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobcard",
            name="reinspection_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="jobcard",
            name="reinspection_done",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="jobcard",
            name="reinspection_done_by",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.CreateModel(
            name="JobCardReInspectionPhoto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="jobcard_reinspection/")),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reinspection_photos", to="core.jobcard")),
            ],
        ),
    ]
