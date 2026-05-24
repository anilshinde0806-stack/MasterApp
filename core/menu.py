from rbac.models import RoleMenuPermission

def menu_context(request):
    if not request.user.is_authenticated:
        return {"menu_items": []}

    user_groups = request.user.groups.all()

    permissions = RoleMenuPermission.objects.filter(
        group__in=user_groups,
        can_view=True
    ).select_related("menu")

    menu_items = []

    for perm in permissions:
        menu_items.append({
            "title": perm.menu.title,
            "url": perm.menu.url_name,
            "can_add": perm.can_add,
            "can_edit": perm.can_edit,
            "can_delete": perm.can_delete,
        })

    return {"menu_items": menu_items}


