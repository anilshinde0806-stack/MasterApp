from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0067_jobcardvehicleconditionphoto"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobcard",
            name="advisor_signature",
            field=models.ImageField(blank=True, null=True, upload_to="jobcard_signatures/"),
        ),
        migrations.AddField(
            model_name="jobcard",
            name="customer_signature",
            field=models.ImageField(blank=True, null=True, upload_to="jobcard_signatures/"),
        ),
    ]
