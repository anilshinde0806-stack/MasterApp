from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0074_line_level_additional_approval_photos"),
    ]

    operations = [
        migrations.AlterField(
            model_name="claim",
            name="intimation_date",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="claim",
            name="survey_date",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="claim",
            name="insurance_approval_date",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="jobcard",
            name="job_date",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name="jobcard",
            name="reinspection_date",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="workallocation",
            name="allotment_date",
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
