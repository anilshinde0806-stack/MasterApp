from rbac.models import RoleMenuPermission, Menu
from django.urls import reverse
from django.urls import resolve

def menu_context(request):
    user = request.user

    if not user.is_authenticated:
        return {"menu_items": []}

    current_url = request.path  # 🔥 current page

    # --- your existing RBAC logic ---
    if user.is_superuser:
        menus = Menu.objects.all().order_by("order")
    else:
        if user.groups.exists():
            perms = RoleMenuPermission.objects.filter(
                group__in=user.groups.all(),
                can_view=True
            ).select_related("menu")
        else:
            perms = []

        menus = [p.menu for p in perms]

        # include parents
        all_menus = {m.id: m for m in menus}
        for m in list(menus):
            parent = m.parent
            while parent:
                all_menus[parent.id] = parent
                parent = parent.parent

        menus = list(all_menus.values())

    menus = list({m.id: m for m in menus}.values())

    # 🔥 build tree + mark active
    menu_dict = {}

    for m in menus:
        is_active = False

        # compare resolved URL
        try:
            from django.urls import reverse
            if m.url:
                if reverse(m.url) == current_url:
                    is_active = True
        except:
            pass

        menu_dict[m.id] = {
            "id": m.id,
            "title": m.name,
            "url": m.url,
            "icon": m.icon,  # ✅ ADD THIS
            "parent_id": m.parent_id,
            "children": [],
            "active": is_active,
        }

    tree = []

    for m in menu_dict.values():
        if m["parent_id"] and m["parent_id"] in menu_dict:
            parent = menu_dict[m["parent_id"]]
            parent["children"].append(m)

            # 🔥 propagate active to parent
            if m["active"]:
                parent["active"] = True
        else:
            tree.append(m)

    return {"menu_items": tree}

def build_breadcrumb(menu_dict):
    # find active node
    active_item = None
    for m in menu_dict.values():
        if m.get("active"):
            active_item = m
            break

    breadcrumb = []

    # walk up parents
    while active_item:
        breadcrumb.append(active_item)
        parent_id = active_item.get("parent_id")
        active_item = menu_dict.get(parent_id)

    breadcrumb.reverse()
    return breadcrumb
from .models import CompanySetup

def company_data(request):

    return {
        'company_setup': CompanySetup.objects.first()
    }