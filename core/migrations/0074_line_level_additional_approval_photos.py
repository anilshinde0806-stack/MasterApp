from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0073_additional_line_approval_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobcardadditionalapprovalphoto",
            name="work_allocation_labour",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="additional_approval_photos",
                to="core.workallocationlabour",
            ),
        ),
        migrations.AddField(
            model_name="jobcardadditionalapprovalphoto",
            name="work_allocation_part",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="additional_approval_photos",
                to="core.workallocationpart",
            ),
        ),
    ]
