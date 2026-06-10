from django.db import migrations


REPORT_TREE = [
    (
        "Workshop Reports",
        "fa fa-industry",
        [
            ("Vehicle Status", "reports/workshop/vehicle-status/"),
            ("Daily In/Out", "daily_in_out_report"),
            ("Control Board", "bodyshop_control_menu"),
            ("Delivery Commitment", "reports/workshop/delivery-commitment/"),
        ],
    ),
    (
        "TAT Reports",
        "fa fa-clock",
        [
            ("TAT Summary", "reports/tat/summary/"),
            ("Delay Analysis", "reports/tat/delay-analysis/"),
            ("Stage Ageing", "reports/tat/stage-ageing/"),
        ],
    ),
    (
        "Insurance Reports",
        "fa fa-file-contract",
        [
            ("Approval Pending", "reports/insurance/approval-pending/"),
            ("Insurance Business", "reports/insurance/business/"),
            ("Surveyor Performance", "surveyor_performance_report"),
        ],
    ),
    (
        "Productivity Reports",
        "fa fa-users-cog",
        [
            ("Work Allocation", "work_allocation_list"),
            ("Technician Productivity", "reports/productivity/technician-productivity/"),
        ],
    ),
    (
        "Financial Reports",
        "fa fa-rupee-sign",
        [
            ("Revenue Summary", "reports/financial/revenue-summary/"),
            ("Labour Revenue", "reports/financial/labour-revenue/"),
            ("Parts Revenue", "reports/financial/parts-revenue/"),
        ],
    ),
    (
        "Graphical Dashboard",
        "fa fa-chart-pie",
        [
            ("KPI Cards", "kpi_cards_report"),
            ("Charts", "reports/dashboard/charts/"),
            ("Control Board", "bodyshop_control_menu"),
        ],
    ),
]


def get_menu(Menu, name, parent=None, defaults=None):
    menu = Menu.objects.filter(name=name, parent=parent).first()
    if menu:
        return menu, False
    defaults = defaults or {}
    return Menu.objects.get_or_create(
        name=name,
        parent=parent,
        defaults=defaults,
    )


def add_reports_menu(apps, schema_editor):
    Menu = apps.get_model("rbac", "Menu")
    UserMenuPermission = apps.get_model("rbac", "UserMenuPermission")
    RoleMenuPermission = apps.get_model("rbac", "RoleMenuPermission")
    User = apps.get_model("auth", "User")
    Group = apps.get_model("auth", "Group")
    Employee = apps.get_model("core", "Employee")

    reports, _ = get_menu(
        Menu,
        "Reports",
        defaults={
            "icon": "fa fa-chart-bar",
            "url": "",
            "order": 80,
        },
    )
    reports.icon = "fa fa-chart-bar"
    reports.url = ""
    reports.order = 80
    reports.save(update_fields=["icon", "url", "order"])

    created_menus = [reports]

    for category_order, (category_name, category_icon, children) in enumerate(REPORT_TREE, start=1):
        category, _ = get_menu(
            Menu,
            category_name,
            parent=reports,
            defaults={
                "icon": category_icon,
                "url": "",
                "order": category_order,
            },
        )
        category.parent = reports
        category.icon = category_icon
        category.url = ""
        category.order = category_order
        category.save(update_fields=["parent", "icon", "url", "order"])
        created_menus.append(category)

        for child_order, (child_name, child_url) in enumerate(children, start=1):
            child, _ = get_menu(
                Menu,
                child_name,
                parent=category,
                defaults={
                    "icon": "fa fa-file-alt",
                    "url": child_url,
                    "order": child_order,
                },
            )
            child.parent = category
            child.icon = child.icon or "fa fa-file-alt"
            child.url = child_url
            child.order = child_order
            child.save(update_fields=["parent", "icon", "url", "order"])
            created_menus.append(child)

    allowed_groups = Group.objects.filter(name__in=["Admin", "Manager", "Floor Supervisor"])
    for group in allowed_groups:
        for menu in created_menus:
            RoleMenuPermission.objects.get_or_create(
                group=group,
                menu=menu,
                defaults={"can_view": True},
            )

    employee_user_ids = Employee.objects.filter(
        user__isnull=False,
        employee_type__in=["ADMIN", "MANAGER", "Floor Supervisor"],
    ).values_list("user_id", flat=True)
    users = User.objects.filter(is_superuser=True) | User.objects.filter(
        id__in=employee_user_ids
    )
    for user in users.distinct():
        for menu in created_menus:
            UserMenuPermission.objects.update_or_create(
                user=user,
                menu=menu,
                defaults={"can_view": True},
            )


def remove_reports_menu(apps, schema_editor):
    Menu = apps.get_model("rbac", "Menu")
    reports = Menu.objects.filter(name="Reports", parent__isnull=True).first()
    if reports:
        reports.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("rbac", "0010_control_board_menu_entry"),
    ]

    operations = [
        migrations.RunPython(add_reports_menu, remove_reports_menu),
    ]
