from django.db import migrations


def create_new_parts_order_menu(apps, schema_editor):
    Menu = apps.get_model("rbac", "Menu")
    RoleMenuPermission = apps.get_model("rbac", "RoleMenuPermission")

    parent = Menu.objects.filter(id=5).first()
    part_order_list = Menu.objects.filter(name="Part Order List").first()

    if part_order_list and part_order_list.parent_id:
        parent = part_order_list.parent

    menu, _ = Menu.objects.get_or_create(
        name="New Parts Order",
        defaults={
            "icon": "fa fa-plus",
            "parent": parent,
            "url": "part_order_create",
            "order": (part_order_list.order + 1) if part_order_list else 1,
        },
    )

    if part_order_list:
        for permission in RoleMenuPermission.objects.filter(menu=part_order_list):
            RoleMenuPermission.objects.get_or_create(
                group=permission.group,
                menu=menu,
                defaults={
                    "can_view": permission.can_view,
                    "can_add": permission.can_add,
                    "can_edit": permission.can_edit,
                    "can_delete": permission.can_delete,
                },
            )


def remove_new_parts_order_menu(apps, schema_editor):
    Menu = apps.get_model("rbac", "Menu")
    Menu.objects.filter(name="New Parts Order", url="part_order_create").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("rbac", "0004_usermenupermission"),
    ]

    operations = [
        migrations.RunPython(
            create_new_parts_order_menu,
            remove_new_parts_order_menu,
        ),
    ]
