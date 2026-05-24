from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0064_claim_invoice_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="claim",
            name="claim_stage",
            field=models.IntegerField(
                choices=[
                    (1, "Claim Created"),
                    (2, "Advisor Assigned"),
                    (3, "Estimate Created"),
                    (4, "Claim Intimation"),
                    (5, "Survey Done"),
                    (6, "Insurance Approval"),
                    (7, "Work Allocation"),
                    (8, "Repair Work In Progress"),
                    (9, "Work Completed"),
                    (10, "Re Inspection"),
                    (11, "Liability"),
                    (12, "Invoiced"),
                    (13, "Delivery"),
                    (14, "Closed"),
                ],
                default=1,
            ),
        ),
    ]
