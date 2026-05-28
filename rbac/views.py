# rbac/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group
from django.db import transaction
from django.shortcuts import  redirect, get_object_or_404, render
from django.contrib.auth.models import  User
from django.views.decorators.http import require_POST
from .models import Menu, RoleMenuPermission, UserMenuPermission


def admin_required(user):
    return user.is_authenticated and user.is_superuser


@login_required
@user_passes_test(admin_required)
def permission_matrix(request):
    groups = Group.objects.all()
    menus = Menu.objects.all()

    matrix = []

    for menu in menus:
        row = {"menu": menu, "permissions": []}

        for group in groups:
            perm = RoleMenuPermission.objects.filter(
                group=group, menu=menu
            ).first()

            row["permissions"].append({
                "group": group,
                "perm": perm
            })

        matrix.append(row)

    return render(request, "rbac/matrix.html", {
        "groups": groups,
        "matrix": matrix
    })


from django.http import JsonResponse


@login_required
@user_passes_test(admin_required)
@require_POST
def update_permission(request):
    menu_id = request.POST.get("menu_id")
    group_id = request.POST.get("group_id")
    perm_type = request.POST.get("perm_type")
    value = request.POST.get("value") == "true"

    menu = Menu.objects.get(id=menu_id)
    group = Group.objects.get(id=group_id)

    perm, _ = RoleMenuPermission.objects.get_or_create(
        menu=menu,
        group=group
    )

    setattr(perm, f"can_{perm_type}", value)
    perm.save()

    return JsonResponse({"status": "ok"})


def build_menu_access_tree(menus, selected_ids):
    menu_map = {}
    tree = []

    for menu in menus:
        menu_map[menu.id] = {
            "menu": menu,
            "checked": menu.id in selected_ids,
            "children": [],
        }

    for node in menu_map.values():
        parent_id = node["menu"].parent_id

        if parent_id and parent_id in menu_map:
            menu_map[parent_id]["children"].append(node)
        else:
            tree.append(node)

    return tree


def build_menu_tree_nodes(menus):
    menu_map = {}
    tree = []

    for menu in menus:
        menu_map[menu.id] = {
            "menu": menu,
            "children": [],
        }

    for node in menu_map.values():
        parent_id = node["menu"].parent_id

        if parent_id and parent_id in menu_map:
            menu_map[parent_id]["children"].append(node)
        else:
            tree.append(node)

    return tree


def build_parent_choices(menus):
    menu_map = {}

    for menu in menus:
        menu_map[menu.id] = {
            "menu": menu,
            "children": [],
        }

    roots = []

    for node in menu_map.values():
        parent_id = node["menu"].parent_id

        if parent_id and parent_id in menu_map:
            menu_map[parent_id]["children"].append(node)
        else:
            roots.append(node)

    choices = []

    def walk(nodes, level=0):
        for node in nodes:
            choices.append({
                "menu": node["menu"],
                "label": ("-- " * level) + node["menu"].name,
            })
            walk(node["children"], level + 1)

    walk(roots)
    return choices


@login_required
@user_passes_test(admin_required)
def menu_manage(request):
    selected_menu = None
    selected_menu_id = request.GET.get("menu_id") or request.POST.get("menu_id") or ""
    selected_parent_id = request.GET.get("parent") or ""

    if selected_menu_id:
        selected_menu = get_object_or_404(Menu, pk=selected_menu_id)
        selected_parent_id = str(selected_menu.parent_id or "")

    if request.method == "POST":
        action = request.POST.get("action", "save")

        if action == "delete" and selected_menu:
            if selected_menu.menu_set.exists():
                messages.error(request, "Remove or move submenu items before deleting this menu.")
            else:
                selected_menu.delete()
                messages.success(request, "Menu deleted successfully.")
                return redirect("menu_manage")

        if action == "save":
            name = request.POST.get("name", "").strip()
            url = request.POST.get("url", "").strip()
            icon = request.POST.get("icon", "").strip()
            order = request.POST.get("order", "0").strip()
            parent_id = request.POST.get("parent") or None

            if not name:
                messages.error(request, "Menu name is required.")
                return redirect(request.get_full_path())

            menu = selected_menu or Menu()
            menu.name = name
            menu.url = url
            menu.icon = icon
            menu.order = int(order) if order.isdigit() else 0
            menu.parent_id = parent_id

            if selected_menu and parent_id:
                parent = Menu.objects.filter(pk=parent_id).first()

                while parent:
                    if parent.id == selected_menu.id:
                        messages.error(request, "A menu cannot be placed under itself.")
                        return redirect(f"{request.path}?menu_id={selected_menu.id}")
                    parent = parent.parent

            menu.save()
            messages.success(request, "Menu saved successfully.")
            return redirect(f"{request.path}?menu_id={menu.id}")

    menus = list(Menu.objects.select_related("parent").order_by(
        "parent_id",
        "order",
        "name"
    ))
    parent_choices = [
        choice for choice in build_parent_choices(menus)
        if not selected_menu or choice["menu"].id != selected_menu.id
    ]

    return render(request, "rbac/menu_manage.html", {
        "menu_tree": build_menu_tree_nodes(menus),
        "parent_choices": parent_choices,
        "selected_menu": selected_menu,
        "selected_parent_id": selected_parent_id,
    })


@login_required
@user_passes_test(admin_required)
def user_access(request):
    users = User.objects.filter(is_active=True).order_by("username")
    selected_user_id = request.POST.get("user_id") or request.GET.get("user_id") or ""
    selected_user = None

    if selected_user_id:
        selected_user = get_object_or_404(User, pk=selected_user_id)

    menus = list(Menu.objects.select_related("parent").order_by(
        "parent_id",
        "order",
        "name"
    ))

    if request.method == "POST" and selected_user:
        selected_menu_ids = {
            int(menu_id)
            for menu_id in request.POST.getlist("menus")
            if menu_id.isdigit()
        }

        menu_by_id = {menu.id: menu for menu in menus}

        for menu_id in list(selected_menu_ids):
            parent = menu_by_id.get(menu_id).parent if menu_id in menu_by_id else None

            while parent:
                selected_menu_ids.add(parent.id)
                parent = parent.parent

        with transaction.atomic():
            for menu in menus:
                UserMenuPermission.objects.update_or_create(
                    user=selected_user,
                    menu=menu,
                    defaults={
                        "can_view": menu.id in selected_menu_ids
                    }
                )

        messages.success(request, "User menu access saved successfully")
        return redirect(f"{request.path}?user_id={selected_user.id}")

    selected_ids = set()

    if selected_user:
        user_permissions = UserMenuPermission.objects.filter(
            user=selected_user
        )

        if user_permissions.exists():
            selected_ids = set(
                user_permissions
                .filter(can_view=True)
                .values_list("menu_id", flat=True)
            )
        elif selected_user.is_superuser:
            selected_ids = {menu.id for menu in menus}
        elif selected_user.groups.exists():
            selected_ids = set(
                RoleMenuPermission.objects.filter(
                    group__in=selected_user.groups.all(),
                    can_view=True
                ).values_list("menu_id", flat=True)
            )

    return render(request, "rbac/user_access.html", {
        "users": users,
        "selected_user": selected_user,
        "selected_user_id": str(selected_user.id) if selected_user else "",
        "menu_tree": build_menu_access_tree(menus, selected_ids),
    })

@login_required
@user_passes_test(admin_required)
def user_create(request):

    menus = (
        Menu.objects
        .prefetch_related(
            "children"
        )
        .filter(
            parent__isnull=True
        )
    )

    if request.method == "POST":

        username = request.POST.get(
            "username"
        )

        password = request.POST.get(
            "password"
        )

        user = User.objects.create_user(

            username=username,

            password=password

        )

        menu_ids = request.POST.getlist(
            "menus"
        )

        for m in menu_ids:

            UserMenuPermission.objects.create(

                user=user,

                menu_id=m

            )

        messages.success(
            request,
            "User created"
        )

        return redirect(
            "user_list"
        )

    return render(

        request,

        "rbac/user_create.html",

        {

            "menus":
                menus

        }

    )
from django.contrib.auth.models import User
from django.shortcuts import render
from .models import Menu, UserMenuPermission


@login_required
@user_passes_test(admin_required)
def user_permission_matrix(request):

    users = User.objects.filter(
        is_active=True
    ).order_by("username")

    menus = Menu.objects.all().order_by(
        "parent_id",
        "order",
        "name"
    )

    matrix = []

    for menu in menus:

        row = {
            "menu": menu,
            "permissions": []
        }

        for user in users:

            perm = UserMenuPermission.objects.filter(
                user=user,
                menu=menu
            ).first()

            row["permissions"].append({
                "user": user,
                "perm": perm
            })

        matrix.append(row)

    return render(request, "rbac/user_matrix.html", {
        "users": users,
        "matrix": matrix
    })
@require_POST
@login_required
@user_passes_test(admin_required)
def update_user_permission(request):

    user_id = request.POST.get("user_id")
    menu_id = request.POST.get("menu_id")
    checked = request.POST.get("checked") == "true"

    if checked:
        UserMenuPermission.objects.update_or_create(
            user_id=user_id,
            menu_id=menu_id,
            defaults={"can_view": True}
        )
    else:
        UserMenuPermission.objects.update_or_create(
            user_id=user_id,
            menu_id=menu_id,
            defaults={"can_view": False}
        )

    return JsonResponse({"status": "success"})
from django.shortcuts import render

@login_required
@user_passes_test(admin_required)
def user_create(request):
    menus = Menu.objects.filter(
        parent__isnull=True
    ).prefetch_related(
        "menu_set"
    )

    return render(
        request,

        "rbac/user_create.html",

        {
            "menus": menus
        }
    )
