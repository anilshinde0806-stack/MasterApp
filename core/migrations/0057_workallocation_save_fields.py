from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0056_partorderheader_vehicle_manual_part_lines"),
    ]

    operations = [
        migrations.AddField(
            model_name="workallocation",
            name="parts_slip_no",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="workallocationpart",
            name="ko_order_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="workallocationpart",
            name="ko_order_no",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="workallocationpart",
            name="pick_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="WorkAllocationLabour",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("decision", models.CharField(default="Approved", max_length=20)),
                ("revised_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("remarks", models.TextField(blank=True)),
                ("allocation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="labours", to="core.workallocation")),
                ("employee", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="core.employee")),
                ("job_labour", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="core.jobcardlabour")),
            ],
        ),
    ]
