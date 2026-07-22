from core.models import Employee


def user_payload(user):
    employee = Employee.objects.filter(user=user).select_related("branch").first()
    employee_type = employee.employee_type if employee else ""
    branch = employee.branch if employee and employee.branch_id else None

    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "is_superuser": user.is_superuser,
        "employee": {
            "id": employee.id if employee else None,
            "name": employee.name if employee else user.get_full_name() or user.username,
            "employee_code": employee.employee_code if employee else "",
            "employee_type": employee_type,
            "designation": employee.designation if employee else "",
            "department": employee.department if employee else "",
            "profile_photo_url": (
                employee.profile_photo.url
                if employee and employee.profile_photo
                else ""
            ),
            "branch": branch.id if branch else "",
            "branch_name": branch.name if branch else "",
            "branch_code": branch.code if branch else "",
        },
        "roles": list(user.groups.values_list("name", flat=True)),
    }


def employee_can_view_all_branches(user, employee=None):
    if user.is_superuser:
        return True
    employee = employee or Employee.objects.filter(user=user).first()
    if not employee:
        return False
    role_text = f"{employee.employee_type or ''} {employee.designation or ''}".upper()
    return (
        employee.employee_type in ["MANAGER", "ADMIN"]
        or "HEAD OFFICE" in role_text
        or "HO" == (employee.branch.code if employee.branch_id else "")
    )


def user_branch(user):
    employee = Employee.objects.filter(user=user).select_related("branch").first()
    return employee.branch if employee and employee.branch_id else None


def branch_filter_queryset(queryset, user, branch_lookup="branch"):
    employee = Employee.objects.filter(user=user).select_related("branch").first()
    if employee_can_view_all_branches(user, employee):
        return queryset
    if employee and employee.branch_id:
        return queryset.filter(**{f"{branch_lookup}_id": employee.branch_id})
    return queryset.filter(**{f"{branch_lookup}__isnull": True})
