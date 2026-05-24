from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0062_workallocation_part_entry_complete"),
    ]

    operations = [
        migrations.AddField(
            model_name="claim",
            name="pre_invoice_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="claim",
            name="pre_invoice_part_amount",
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="claim",
            name="pre_invoice_labour_amount",
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="claim",
            name="pre_invoice_total_amount",
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="claim",
            name="pre_invoice_file",
            field=models.FileField(blank=True, null=True, upload_to="claim_pre_invoices/"),
        ),
        migrations.AddField(
            model_name="claim",
            name="liability_received_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="claim",
            name="liability_do_amount",
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="claim",
            name="liability_document",
            field=models.FileField(blank=True, null=True, upload_to="claim_liability_documents/"),
        ),
    ]
