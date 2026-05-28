from django.db import migrations


def create_menu_manager_menu(apps, schema_editor):
    Menu = apps.get_model("rbac", "Menu")
    RoleMenuPermission = apps.get_model("rbac", "RoleMenuPermission")
    Group = apps.get_model("auth", "Group")

    admin_menu, _ = Menu.objects.get_or_create(
        name="Admin",
        defaults={
            "icon": "fa fa-user-shield",
            "url": "",
            "order": 99,
        },
    )

    menu_manager, _ = Menu.objects.get_or_create(
        name="Menu Manager",
        defaults={
            "icon": "fa fa-bars",
            "parent": admin_menu,
            "url": "menu_manage",
            "order": 5,
        },
    )

    if menu_manager.parent_id != admin_menu.id or menu_manager.url != "menu_manage":
        menu_manager.parent = admin_menu
        menu_manager.url = "menu_manage"
        menu_manager.icon = menu_manager.icon or "fa fa-bars"
        menu_manager.save(update_fields=["parent", "url", "icon"])

    admin_group = Group.objects.filter(name__iexact="Admin").first()

    if admin_group:
        RoleMenuPermission.objects.get_or_create(
            group=admin_group,
            menu=admin_menu,
            defaults={"can_view": True},
        )
        RoleMenuPermission.objects.get_or_create(
            group=admin_group,
            menu=menu_manager,
            defaults={"can_view": True},
        )


def remove_menu_manager_menu(apps, schema_editor):
    Menu = apps.get_model("rbac", "Menu")
    Menu.objects.filter(name="Menu Manager", url="menu_manage").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("rbac", "0006_user_access_menu"),
    ]

    operations = [
        migrations.RunPython(create_menu_manager_menu, remove_menu_manager_menu),
    ]
