from django.urls import NoReverseMatch, reverse

from rbac.models import Menu, RoleMenuPermission, UserMenuPermission


def allowed_menus_for_user(user):
    if user.is_superuser:
        menus = list(Menu.objects.all().order_by("order", "name"))
    else:
        user_permissions = UserMenuPermission.objects.filter(user=user).select_related(
            "menu", "menu__parent"
        )
        if user_permissions.exists():
            menus = [permission.menu for permission in user_permissions if permission.can_view]
        elif user.groups.exists():
            role_permissions = RoleMenuPermission.objects.filter(
                group__in=user.groups.all(),
                can_view=True,
            ).select_related("menu", "menu__parent")
            menus = [permission.menu for permission in role_permissions]
        else:
            menus = []

        all_menus = {menu.id: menu for menu in menus}
        for menu in list(menus):
            parent = menu.parent
            while parent:
                all_menus[parent.id] = parent
                parent = parent.parent
        menus = list(all_menus.values())

    return list({menu.id: menu for menu in menus}.values())


def menu_href(menu):
    if not menu.url:
        return "#"
    try:
        return reverse(menu.url)
    except NoReverseMatch:
        return "/" + menu.url.strip("/")


def build_menu_tree(menus):
    menu_map = {
        menu.id: {
            "id": menu.id,
            "title": menu.name,
            "url": menu.url,
            "href": menu_href(menu),
            "icon": menu.icon,
            "parent_id": menu.parent_id,
            "children": [],
        }
        for menu in menus
    }

    tree = []
    for item in menu_map.values():
        parent_id = item["parent_id"]
        if parent_id and parent_id in menu_map:
            menu_map[parent_id]["children"].append(item)
        else:
            tree.append(item)
    return tree
