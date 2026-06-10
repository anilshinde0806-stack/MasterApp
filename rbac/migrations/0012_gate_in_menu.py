from django.db import migrations


def add_gate_in_menu(apps, schema_editor):
    Menu = apps.get_model("rbac", "Menu")
    RoleMenuPermission = apps.get_model("rbac", "RoleMenuPermission")
    UserMenuPermission = apps.get_model("rbac", "UserMenuPermission")
    Employee = apps.get_model("core", "Employee")

    parent, _ = Menu.objects.get_or_create(
        name="WorkShop/Floor",
        parent=None,
        defaults={
            "icon": "fa fa-industry",
            "url": "",
            "order": 30,
        },
    )

    menu, _ = Menu.objects.get_or_create(
        name="Gate In Entry",
        parent=parent,
        defaults={
            "url": "gate_in_entry",
            "icon": "fa fa-sign-in",
            "order": 0,
        },
    )
    menu.url = "gate_in_entry"
    menu.icon = menu.icon or "fa fa-sign-in"
    menu.order = 0
    menu.save(update_fields=["url", "icon", "order"])

    for permission in RoleMenuPermission.objects.filter(menu=parent):
        RoleMenuPermission.objects.get_or_create(
            group=permission.group,
            menu=menu,
            defaults={"can_view": permission.can_view},
        )

    gate_users = Employee.objects.filter(
        user__isnull=False,
        employee_type__icontains="Gate",
    ) | Employee.objects.filter(
        user__isnull=False,
        designation__icontains="Security",
    )

    for employee in gate_users:
        UserMenuPermission.objects.get_or_create(
            user=employee.user,
            menu=parent,
            defaults={"can_view": True},
        )
        UserMenuPermission.objects.update_or_create(
            user=employee.user,
            menu=menu,
            defaults={"can_view": True},
        )


def remove_gate_in_menu(apps, schema_editor):
    Menu = apps.get_model("rbac", "Menu")
    Menu.objects.filter(name="Gate In Entry", url="gate_in_entry").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("rbac", "0011_reports_menu_structure"),
    ]

    operations = [
        migrations.RunPython(add_gate_in_menu, remove_gate_in_menu),
    ]
