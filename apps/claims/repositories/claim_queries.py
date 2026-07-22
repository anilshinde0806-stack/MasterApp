"""Shared read model for desktop and mobile Claim presentations."""

from django.db.models import Q

from core.models import Claim, ClaimStageCode, Employee


class ClaimQueryService:
    """Owns Claim visibility, filtering, and eager-loading rules."""

    @staticmethod
    def employee_for(user):
        return Employee.objects.filter(user=user).select_related("branch").first()

    @classmethod
    def visible_to(cls, user):
        employee = cls.employee_for(user)
        queryset = Claim.objects.all()
        role = (employee.employee_type or "").upper() if employee else ""
        is_admin_group = user.groups.filter(name__iexact="Admin").exists()
        is_manager_group = user.groups.filter(name__iexact="Manager").exists()

        if (
            user.is_superuser
            or role == "ADMIN"
            or is_admin_group
        ):
            return queryset

        if not employee or not employee.branch_id:
            return queryset.none()

        queryset = queryset.filter(branch_id=employee.branch_id)
        if role == "MANAGER" or is_manager_group:
            return queryset
        if role == "ADVISOR":
            return queryset.filter(employee=employee)
        if role in {"STAFF", "RECEPTION"}:
            return queryset.filter(employee__isnull=True)
        return queryset

    @classmethod
    def filtered(
        cls,
        user,
        *,
        branch_id=None,
        from_date=None,
        to_date=None,
        status="open",
        advisor_blank=False,
        advisor_assigned=False,
    ):
        queryset = cls.visible_to(user)
        employee = cls.employee_for(user)
        is_admin = bool(
            user.is_superuser
            or user.groups.filter(name__iexact="Admin").exists()
            or (
                employee
                and (employee.employee_type or "").upper() == "ADMIN"
            )
        )

        if is_admin and branch_id and str(branch_id).lower() != "all":
            queryset = queryset.filter(branch_id=branch_id)

        status_value = (status or "open").strip().lower()
        closed = Q(claim_stage=ClaimStageCode.CLOSED) | Q(status__iexact="Closed")
        if status_value == "closed":
            queryset = queryset.filter(closed)
        elif status_value != "all":
            queryset = queryset.exclude(closed | Q(status__iexact="Cancelled"))

        if from_date:
            queryset = queryset.filter(created_at__date__gte=from_date)
        if to_date:
            queryset = queryset.filter(created_at__date__lte=to_date)
        if advisor_blank:
            queryset = queryset.filter(employee__isnull=True)
        if advisor_assigned:
            queryset = queryset.filter(employee__isnull=False)

        return queryset.select_related(
            "branch",
            "vehicle",
            "vehicle__model",
            "vehicle__variant",
            "vehicle__customer",
            "employee",
            "insurance_company",
            "surveyor",
            "jobcard",
        )
