from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("core", "0106_gatein_gateout_evidence")]
    operations = [migrations.AddField(model_name="gateinentry", name="out_km", field=models.PositiveIntegerField(blank=True, null=True))]
