from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0068_jobcard_signatures"),
    ]

    operations = [
        migrations.AddField(
            model_name="claim",
            name="self_survey",
            field=models.BooleanField(default=False),
        ),
    ]
