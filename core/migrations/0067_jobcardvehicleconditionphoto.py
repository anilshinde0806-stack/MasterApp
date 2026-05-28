from django.db import migrations, models
import django.db.models.deletion
import core.models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0066_claim_delivered_by_claim_delivered_to_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="JobCardVehicleConditionPhoto",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("caption", models.CharField(max_length=100)),
                ("image", models.ImageField(upload_to=core.models.vehicle_condition_photo_upload_path)),
                ("uploaded_at", models.DateTimeField(auto_now=True)),
                ("job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="vehicle_condition_photos", to="core.jobcard")),
            ],
        ),
        migrations.AddConstraint(
            model_name="jobcardvehicleconditionphoto",
            constraint=models.UniqueConstraint(fields=("job", "caption"), name="unique_jobcard_vehicle_condition_caption"),
        ),
    ]
