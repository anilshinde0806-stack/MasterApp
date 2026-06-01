from django.db import migrations


def update_control_board_menu(apps, schema_editor):
    Menu = apps.get_model("rbac", "Menu")
    UserMenuPermission = apps.get_model("rbac", "UserMenuPermission")
    RoleMenuPermission = apps.get_model("rbac", "RoleMenuPermission")
    Employee = apps.get_model("core", "Employee")

    parent, _ = Menu.objects.get_or_create(
        name="WorkShop/Floor",
        defaults={
            "icon": "fa fa-industry",
            "url": "",
            "order": 30,
        },
    )

    menu, _ = Menu.objects.get_or_create(
        name="Bodyshop Control Board",
        defaults={
            "parent": parent,
            "url": "bodyshop_control_menu",
            "icon": "fa fa-table",
            "order": 1,
        },
    )
    menu.parent = parent
    menu.url = "bodyshop_control_menu"
    menu.icon = menu.icon or "fa fa-table"
    menu.order = 1
    menu.save(update_fields=["parent", "url", "icon", "order"])

    for permission in RoleMenuPermission.objects.filter(menu=parent):
        RoleMenuPermission.objects.get_or_create(
            group=permission.group,
            menu=menu,
            defaults={"can_view": permission.can_view},
        )

    floor_users = Employee.objects.filter(
        user__isnull=False,
        employee_type__icontains="Floor",
    ) | Employee.objects.filter(
        user__isnull=False,
        designation__icontains="Floor",
    )

    for employee in floor_users:
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


def revert_control_board_menu(apps, schema_editor):
    Menu = apps.get_model("rbac", "Menu")
    Menu.objects.filter(
        name="Bodyshop Control Board",
        url="bodyshop_control_menu",
    ).update(url="bodyshop_control_board")


class Migration(migrations.Migration):

    dependencies = [
        ("rbac", "0009_bodyshop_control_board_menu"),
    ]

    operations = [
        migrations.RunPython(
            update_control_board_menu,
            revert_control_board_menu,
        ),
    ]
