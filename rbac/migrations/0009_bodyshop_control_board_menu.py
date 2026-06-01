from django.db import migrations


def add_bodyshop_control_board_menu(apps, schema_editor):
    Menu = apps.get_model("rbac", "Menu")
    RoleMenuPermission = apps.get_model("rbac", "RoleMenuPermission")
    UserMenuPermission = apps.get_model("rbac", "UserMenuPermission")
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
            "url": "bodyshop_control_board",
            "icon": "fa fa-table",
            "order": 1,
        },
    )

    changed = False
    if menu.parent_id != parent.id:
        menu.parent = parent
        changed = True
    if menu.url != "bodyshop_control_board":
        menu.url = "bodyshop_control_board"
        changed = True
    if not menu.icon:
        menu.icon = "fa fa-table"
        changed = True
    if changed:
        menu.save()

    for permission in RoleMenuPermission.objects.filter(menu=parent):
        RoleMenuPermission.objects.get_or_create(
            group=permission.group,
            menu=menu,
            defaults={"can_view": permission.can_view},
        )

    floor_users = Employee.objects.filter(
        user__isnull=False,
    ).filter(
        employee_type__icontains="Floor"
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


def remove_bodyshop_control_board_menu(apps, schema_editor):
    Menu = apps.get_model("rbac", "Menu")
    Menu.objects.filter(
        name="Bodyshop Control Board",
        url="bodyshop_control_board",
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0074_line_level_additional_approval_photos"),
        ("rbac", "0008_part_master_menu"),
    ]

    operations = [
        migrations.RunPython(
            add_bodyshop_control_board_menu,
            remove_bodyshop_control_board_menu,
        ),
    ]
