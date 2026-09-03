from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0101_employee_quality_inspector_type"),
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
                    ("Parts Manager", "Parts Manager"),
                ],
                default="STAFF",
                max_length=20,
            ),
        ),
    ]
