from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0063_claim_liability_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="claim",
            name="invoice_datetime",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="claim",
            name="invoice_amount",
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="claim",
            name="invoice_parts_amount",
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="claim",
            name="invoice_labour_amount",
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="claim",
            name="customer_difference_amount",
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="claim",
            name="payment_mode",
            field=models.CharField(blank=True, choices=[("Online", "Online"), ("UPI", "UPI"), ("Card", "Card"), ("Cash", "Cash"), ("DD", "DD"), ("Other", "Other")], max_length=20),
        ),
        migrations.AddField(
            model_name="claim",
            name="payment_details",
            field=models.TextField(blank=True),
        ),
    ]
