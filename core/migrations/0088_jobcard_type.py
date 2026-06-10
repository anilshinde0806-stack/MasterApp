from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0087_gate_in_gate_out"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobcard",
            name="jobcard_type",
            field=models.CharField(
                choices=[
                    ("Cashless", "Cashless"),
                    ("NonCashless", "Non-Cashless"),
                    ("Paid", "Paid"),
                    ("FOC", "FOC"),
                    ("Warranty", "Warranty"),
                ],
                default="Paid",
                max_length=30,
            ),
        ),
    ]
