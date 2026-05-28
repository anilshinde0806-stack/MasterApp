from django.db import migrations


def create_user_access_menu(apps, schema_editor):
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

    user_access_menu, _ = Menu.objects.get_or_create(
        name="User Access",
        defaults={
            "icon": "fa fa-lock",
            "parent": admin_menu,
            "url": "user_access",
            "order": 10,
        },
    )

    if user_access_menu.parent_id != admin_menu.id or user_access_menu.url != "user_access":
        user_access_menu.parent = admin_menu
        user_access_menu.url = "user_access"
        user_access_menu.icon = user_access_menu.icon or "fa fa-lock"
        user_access_menu.save(update_fields=["parent", "url", "icon"])

    admin_group = Group.objects.filter(name__iexact="Admin").first()

    if admin_group:
        RoleMenuPermission.objects.get_or_create(
            group=admin_group,
            menu=admin_menu,
            defaults={"can_view": True},
        )
        RoleMenuPermission.objects.get_or_create(
            group=admin_group,
            menu=user_access_menu,
            defaults={"can_view": True},
        )


def remove_user_access_menu(apps, schema_editor):
    Menu = apps.get_model("rbac", "Menu")
    Menu.objects.filter(name="User Access", url="user_access").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("rbac", "0005_new_parts_order_menu"),
    ]

    operations = [
        migrations.RunPython(create_user_access_menu, remove_user_access_menu),
    ]
