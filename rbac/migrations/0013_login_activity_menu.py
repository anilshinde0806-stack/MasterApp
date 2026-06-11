from django.db import migrations


def create_login_activity_menu(apps, schema_editor):
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

    login_activity, _ = Menu.objects.get_or_create(
        name="Login Activity",
        defaults={
            "icon": "fa fa-clock-rotate-left",
            "parent": admin_menu,
            "url": "login_activity",
            "order": 20,
        },
    )

    changed = False
    if login_activity.parent_id != admin_menu.id:
        login_activity.parent = admin_menu
        changed = True
    if login_activity.url != "login_activity":
        login_activity.url = "login_activity"
        changed = True
    if not login_activity.icon:
        login_activity.icon = "fa fa-clock-rotate-left"
        changed = True
    if changed:
        login_activity.save(update_fields=["parent", "url", "icon"])

    admin_group = Group.objects.filter(name__iexact="Admin").first()
    if admin_group:
        RoleMenuPermission.objects.get_or_create(
            group=admin_group,
            menu=admin_menu,
            defaults={"can_view": True},
        )
        RoleMenuPermission.objects.get_or_create(
            group=admin_group,
            menu=login_activity,
            defaults={"can_view": True},
        )


def remove_login_activity_menu(apps, schema_editor):
    Menu = apps.get_model("rbac", "Menu")
    Menu.objects.filter(name="Login Activity", url="login_activity").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("rbac", "0012_gate_in_menu"),
    ]

    operations = [
        migrations.RunPython(create_login_activity_menu, remove_login_activity_menu),
    ]
