from core.models import Branch


def get_user_branch(user):
    """
    Returns the user's assigned branch.
    """
    employee = getattr(user, "employee", None)
    if employee is None:
        return None

    return employee.branch


def resolve_branch(user, branch_param):
    """
    Returns the effective Branch object or None (All Branches).

    Admin:
        ?branch=all
        ?branch=2

    Others:
        always own branch
    """

    employee = getattr(user, "employee", None)

    if employee is None:
        return None

    if employee.employee_type == "ADMIN":

        if not branch_param or branch_param == "all":
            return None

        return Branch.objects.filter(
            pk=branch_param,
            is_active=True,
        ).first()

    return employee.branch


def filter_branch(queryset, branch):
    if branch is None:
        return queryset

    return queryset.filter(branch=branch)