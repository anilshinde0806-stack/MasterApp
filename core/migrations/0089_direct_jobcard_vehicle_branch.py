from django.db import migrations, models
import django.db.models.deletion


def populate_jobcard_vehicle_branch(apps, schema_editor):
    JobCard = apps.get_model("core", "JobCard")
    for job in JobCard.objects.select_related("claim", "claim__vehicle", "claim__branch"):
        update_fields = []
        if job.claim_id and job.claim.vehicle_id and not job.vehicle_id:
            job.vehicle_id = job.claim.vehicle_id
            update_fields.append("vehicle")
        if job.claim_id and job.claim.branch_id and not job.branch_id:
            job.branch_id = job.claim.branch_id
            update_fields.append("branch")
        if update_fields:
            job.save(update_fields=update_fields)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0088_jobcard_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="jobcard",
            name="claim",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="core.claim",
            ),
        ),
        migrations.AddField(
            model_name="jobcard",
            name="vehicle",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="direct_jobcards",
                to="core.vehicle",
            ),
        ),
        migrations.AddField(
            model_name="jobcard",
            name="branch",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="jobcards",
                to="core.branch",
            ),
        ),
        migrations.RunPython(populate_jobcard_vehicle_branch, migrations.RunPython.noop),
    ]
