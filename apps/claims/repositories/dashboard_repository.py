"""Shared dashboard aggregate and lookup data access."""

import json
from decimal import Decimal

from django.db import connection
from django.db.models import Q

from core.models import Branch, Employee


class DashboardMetricsRepository:
    FUNCTION_NAME = "bodyshop_dashboard_metrics"

    @classmethod
    def is_available(cls):
        if connection.vendor != "postgresql":
            return False
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT to_regprocedure(%s) IS NOT NULL",
                [f"{cls.FUNCTION_NAME}(bigint[],bigint[],bigint[],date,date)"],
            )
            return cursor.fetchone()[0]

    @classmethod
    def get(
        cls, *, claim_ids, period_claim_ids, jobcard_ids, start_date, end_date
    ):
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT * FROM {cls.FUNCTION_NAME}(%s, %s, %s, %s, %s)",
                [
                    list(claim_ids),
                    list(period_claim_ids),
                    list(jobcard_ids),
                    start_date,
                    end_date,
                ],
            )
            columns = [column[0] for column in cursor.description]
            row = cursor.fetchone()
        values = dict(zip(columns, row)) if row else {}
        for key in ("stage_counts", "advisor_counts"):
            if isinstance(values.get(key), str):
                values[key] = json.loads(values[key])
        return values


class DashboardKPIRepository:
    """Compact KPI read model used by the Flutter Admin dashboard."""

    FUNCTION_NAME = "bodyshop_dashboard_kpis"

    @classmethod
    def is_available(cls):
        if connection.vendor != "postgresql":
            return False
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT to_regprocedure(%s) IS NOT NULL",
                [f"{cls.FUNCTION_NAME}(bigint[],bigint[])"],
            )
            return cursor.fetchone()[0]

    @classmethod
    def get(cls, *, claim_ids, jobcard_ids):
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT * FROM {cls.FUNCTION_NAME}(%s, %s)",
                [list(claim_ids), list(jobcard_ids)],
            )
            columns = [column[0] for column in cursor.description]
            row = cursor.fetchone()
        values = dict(zip(columns, row)) if row else {}
        if isinstance(values.get("pipeline_counts"), str):
            values["pipeline_counts"] = json.loads(values["pipeline_counts"])
        return values


class DashboardLookupRepository:
    @staticmethod
    def employee_for_user(user):
        return Employee.objects.select_related("user", "branch").filter(user=user).first()

    @staticmethod
    def active_branches():
        return Branch.objects.filter(is_active=True).order_by("name")

    @staticmethod
    def advisor_options(*, employee=None, selected_branch=None, is_admin=False):
        queryset = Employee.objects.filter(is_active=True).filter(
            Q(employee_type__iexact="Advisor")
            | Q(designation__iexact="Advisor")
        )
        if (
            employee
            and employee.employee_type == "MANAGER"
            and employee.branch_id
            and not is_admin
        ):
            queryset = queryset.filter(branch=employee.branch)
        elif selected_branch:
            queryset = queryset.filter(branch=selected_branch)
        return queryset.order_by("name")

    @staticmethod
    def recent_jobs(jobcards, limit=10):
        return jobcards.select_related(
            "claim", "claim__vehicle", "advisor"
        ).order_by("-id")[:limit]
