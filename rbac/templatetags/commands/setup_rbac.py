from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, User
from rbac.models import Menu, RoleMenuPermission


class Command(BaseCommand):
    help = "Setup RBAC (roles, menus, permissions)"

    def handle(self, *args, **kwargs):

        self.stdout.write(self.style.WARNING("🚀 Setting up RBAC..."))

        # 🔷 1. Create Roles
        roles = ["Admin", "Manager", "Staff"]
        groups = {}

        for role in roles:
            group, created = Group.objects.get_or_create(name=role)
            groups[role] = group
            self.stdout.write(f"✔ Role: {role} {'(created)' if created else '(exists)'}")

        # 🔷 2. Create Menus
        menu_data = [
            {"title": "Dashboard", "url_name": "dashboard"},
            {"title": "Bookings", "url_name": "dashboard"},
            {"title": "Add Booking", "url_name": "dashboard"},
        ]

        menus = {}
        for item in menu_data:
            menu, created = Menu.objects.get_or_create(
                title=item["title"],
                defaults={"url_name": item["url_name"]}
            )
            menus[item["title"]] = menu
            self.stdout.write(f"✔ Menu: {item['title']}")

        # 🔷 3. Assign Menu Permissions

        # Admin → all access
        for menu in menus.values():
            RoleMenuPermission.objects.get_or_create(
                group=groups["Admin"],
                menu=menu,
                defaults={
                    "can_view": True,
                    "can_add": True,
                    "can_edit": True,
                    "can_delete": True,
                }
            )

        # Manager → limited
        RoleMenuPermission.objects.get_or_create(
            group=groups["Manager"],
            menu=menus["Dashboard"],
            defaults={"can_view": True}
        )

        RoleMenuPermission.objects.get_or_create(
            group=groups["Manager"],
            menu=menus["Bookings"],
            defaults={"can_view": True, "can_add": True}
        )

        # Staff → minimal
        RoleMenuPermission.objects.get_or_create(
            group=groups["Staff"],
            menu=menus["Dashboard"],
            defaults={"can_view": True}
        )

        # 🔷 4. Assign superuser to Admin group (optional)
        try:
            superuser = User.objects.filter(is_superuser=True).first()
            if superuser:
                superuser.groups.add(groups["Admin"])
                self.stdout.write("✔ Superuser added to Admin group")
        except Exception:
            pass

        self.stdout.write(self.style.SUCCESS("✅ RBAC setup complete!"))