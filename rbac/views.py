# rbac/views.py
from django.contrib import messages
from django.shortcuts import  redirect
from django.contrib.auth.models import  User
from django.views.decorators.http import require_POST


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


from django.shortcuts import render

# Create your views here.
# rbac/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import RoleMenuPermission
from django.contrib.auth.models import Group

@csrf_exempt
def update_permission(request):
    if request.method == "POST":
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
from rbac.models import (
    Menu,
    UserMenuPermission
)

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
        UserMenuPermission.objects.filter(
            user_id=user_id,
            menu_id=menu_id
        ).delete()

    return JsonResponse({"status": "success"})
from django.shortcuts import render

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