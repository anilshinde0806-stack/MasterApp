from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0105_partrequisitionline_estimated_part")]
    operations = [
        migrations.AddField(model_name="gateinentry", name="gate_pass_no", field=models.CharField(blank=True, max_length=80)),
        migrations.AddField(model_name="gateinentry", name="gate_pass_evidence", field=models.ImageField(blank=True, null=True, upload_to="gate_pass/evidence/")),
        migrations.AddField(model_name="gateinentry", name="customer_signature", field=models.ImageField(blank=True, null=True, upload_to="gate_pass/signatures/")),
    ]
