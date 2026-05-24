from django import template
from rbac.models import Menu

register = template.Library()


def has_permission(user, menu):
    if not menu.permissions.exists():
        return True
    return user.has_perms([p.codename for p in menu.permissions.all()])


def build_menu_tree(user, parent=None):
    menus = Menu.objects.filter(parent=parent).order_by('order')
    tree = []

    for menu in menus:
        if not has_permission(user, menu):
            continue

        children = build_menu_tree(user, menu)

        tree.append({
            "menu": menu,
            "children": children
        })

    return tree


@register.inclusion_tag('rbac/sidebar.html', takes_context=True)
def render_sidebar(context):
    user = context['request'].user
    menu_tree = build_menu_tree(user)
    return {"menu_tree": menu_tree}