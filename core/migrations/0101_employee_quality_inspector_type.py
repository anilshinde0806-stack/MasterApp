from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0100_quality_check_inspector_signatures"),
    ]

    operations = [
        migrations.AlterField(
            model_name="employee",
            name="employee_type",
            field=models.CharField(
                choices=[
                    ("ADMIN", "Admin"),
                    ("STAFF", "Staff"),
                    ("Advisor", "Advisor"),
                    ("MANAGER", "Manager"),
                    ("Floor Supervisor", "Floor Supervisor"),
                    ("Gate Security", "Gate Security"),
                    ("Reception", "Reception"),
                    ("Quality Inspector", "Quality Inspector"),
                ],
                default="STAFF",
                max_length=20,
            ),
        ),
    ]
