from django.db import migrations


def add_part_master_menu(apps, schema_editor):
    Menu = apps.get_model("rbac", "Menu")
    RoleMenuPermission = apps.get_model("rbac", "RoleMenuPermission")

    parent, _ = Menu.objects.get_or_create(
        name="Part",
        defaults={
            "url": "",
            "icon": "fa fa-cogs",
            "order": 3,
        },
    )

    if parent.url == "#":
        parent.url = ""
        parent.save(update_fields=["url"])

    part_master, _ = Menu.objects.get_or_create(
        name="Part Master",
        defaults={
            "parent": parent,
            "url": "part",
            "icon": "fa fa-cog",
            "order": 0,
        },
    )

    if part_master.parent_id != parent.id or part_master.url != "part":
        part_master.parent = parent
        part_master.url = "part"
        part_master.icon = part_master.icon or "fa fa-cog"
        part_master.order = 0
        part_master.save(update_fields=["parent", "url", "icon", "order"])

    for permission in RoleMenuPermission.objects.filter(menu=parent):
        RoleMenuPermission.objects.get_or_create(
            group=permission.group,
            menu=part_master,
            defaults={
                "can_view": permission.can_view,
                "can_add": permission.can_add,
                "can_edit": permission.can_edit,
                "can_delete": permission.can_delete,
            },
        )


def remove_part_master_menu(apps, schema_editor):
    Menu = apps.get_model("rbac", "Menu")
    Menu.objects.filter(name="Part Master", url="part").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("rbac", "0007_menu_manager_menu"),
    ]

    operations = [
        migrations.RunPython(add_part_master_menu, remove_part_master_menu),
    ]
