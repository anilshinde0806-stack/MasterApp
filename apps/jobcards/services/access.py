from apps.accounts.services.user_context import branch_filter_queryset, employee_can_view_all_branches
from core.models import Claim, Employee, JobCard


def dashboard_querysets_for_user(user):
    employee = Employee.objects.filter(user=user).select_related("branch").first()
    all_claims = branch_filter_queryset(Claim.objects.all(), user)
    all_jobcards = branch_filter_queryset(JobCard.objects.all(), user, "claim__branch")

    if employee_can_view_all_branches(user, employee):
        return all_claims, all_jobcards

    if employee and employee.employee_type in ["MANAGER", "ADMIN"]:
        return all_claims, all_jobcards

    if employee and employee.employee_type == "Advisor":
        return (
            Claim.objects.filter(employee=employee),
            JobCard.objects.filter(advisor=employee),
        )

    if employee and employee.employee_type in ["STAFF", "RECEPTION"]:
        return all_claims.filter(employee__isnull=True), JobCard.objects.none()

    if employee and (employee.employee_type or "").strip().upper() == "FLOOR SUPERVISOR":
        return Claim.objects.all(), JobCard.objects.all()

    return Claim.objects.none(), JobCard.objects.none()
