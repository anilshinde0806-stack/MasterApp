from django.db.models import Count, Q
from core.models import UserNotification, WorkProgress
from apps.claims.repositories.dashboard_repository import DashboardLookupRepository


class BaseDashboardService:

    def __init__(self, user, branch=None, employee=None):
        self.user = user
        self.branch = branch

        self.employee = employee or DashboardLookupRepository.employee_for_user(user)

    # Move these methods here:
    # _base_dashboard()
    def _base_dashboard(self):
        return {

            "dashboard_type": "",

            "user": self._get_user(),

            "notification_count": self._get_notification_count(),

            # Common
            "summaries": [],
            "pipeline": [],
            "performance": self._empty_performance(),

            # Admin Analytics
            "financial": self._empty_financial(),
            "top_advisors": [],
            "top_technicians": [],
            "branch_performance": [],

            # Operational
            "actions": [],
            "recent_works": [],

            # Future
            "alerts": [],
            "announcements": [],
        }
    # _get_user()
    def _get_user(self, employee=None):
        employee = employee or self.employee

        return {
            "id": employee.id if employee else None,
            "name": (
                employee.name
                if employee
                else self.user.get_full_name() or self.user.username
            ),
            "employee_type": employee.employee_type if employee else "",
            "designation": employee.designation if employee else "",
            "department": employee.department if employee else "",
            "branch": (
                employee.branch.name
                if employee and employee.branch
                else ""
            ),
            "profile_image": (
                employee.profile_photo.url
                if employee and employee.profile_photo
                else None
            ),
        }

    # _get_work_queryset()

    # ------------------------------------------------------------------
    # Work Query
    # ------------------------------------------------------------------

    def _get_work_queryset(self, employee, branch):

        queryset = (
            WorkProgress.objects
            .select_related(
                "allocation",
                "allocation__job",
                "allocation__job__vehicle",
                "allocation__job__vehicle__customer",
                "allocation__job__advisor",
                "employee",
            )
        )

        role = (employee.employee_type or "").upper()

        # ADMIN
        if role == "ADMIN":
            if branch is not None:
                queryset = queryset.filter(
                    allocation__job__branch=branch
                )
            return queryset

        # MANAGER
        if role == "MANAGER":
            return queryset.filter(
                allocation__job__branch=employee.branch
            )

        # ADVISOR
        if role == "ADVISOR":
            return queryset.filter(
                allocation__job__advisor=employee
            )

        # TECHNICIAN / STAFF
        return queryset.filter(
            employee=employee
        )
        # ------------------------------------------------------------------
        # Helpers
        # ------------------------------------------------------------------

    @staticmethod
    def _get_status(progress):

        if progress.finish_time:
            return "Completed"

        if progress.start_time:
            return "In Progress"

        return "Assigned"
    # _get_actions()
    def _get_actions(self, employee):
        employee_type = (employee.employee_type or "").upper()
        designation = (employee.designation or "").upper()

        # ---------------------------------------------------------
        # ADMIN / MANAGER
        # ---------------------------------------------------------
        if employee_type in ["ADMIN", "MANAGER"]:
            return [
                {
                    "id": 1,
                    "title": "Claims",
                    "icon": "description",
                    "route": "/claims",
                    "color": "#1976D2",
                },
                {
                    "id": 2,
                    "title": "Job Cards",
                    "icon": "engineering",
                    "route": "/jobcards",
                    "color": "#00897B",
                },
                {
                    "id": 3,
                    "title": "Customers",
                    "icon": "groups",
                    "route": "/customers",
                    "color": "#F57C00",
                },
                {
                    "id": 4,
                    "title": "Vehicles",
                    "icon": "directions_car",
                    "route": "/vehicles",
                    "color": "#8E24AA",
                },
                {
                    "id": 5,
                    "title": "Reports",
                    "icon": "bar_chart",
                    "route": "/reports",
                    "color": "#D81B60",
                },
                {
                    "id": 6,
                    "title": "Employees",
                    "icon": "badge",
                    "route": "/employees",
                    "color": "#3949AB",
                },
            ]
    # _get_notification_count()
    def _get_notification_count(self):

        if not self.user.is_authenticated:
            return 0

        return UserNotification.objects.filter(
            user=self.user,
            is_read=False,
        ).count()

    # _get_summaries()
    def _get_summaries(self, work):

        stats = work.aggregate(
            assigned=Count(
                "id",
                filter=Q(start_time__isnull=True),
            ),
            running=Count(
                "id",
                filter=Q(
                    start_time__isnull=False,
                    finish_time__isnull=True,
                ),
            ),
            completed=Count(
                "id",
                filter=Q(finish_time__isnull=False),
            ),
        )

        return [
            {
                "title": "Assigned",
                "value": stats["assigned"],
                "type": "assigned",
            },
            {
                "title": "Repair",
                "value": stats["running"],
                "type": "repair",
            },
            {
                "title": "Completed",
                "value": stats["completed"],
                "type": "completed",
            },
        ]
    # _get_performance()

    def _get_performance(self, work):
        stats = work.aggregate(
            total=Count("id"),
            completed=Count(
                "id",
                filter=Q(finish_time__isnull=False),
            ),
            running=Count(
                "id",
                filter=Q(
                    start_time__isnull=False,
                    finish_time__isnull=True,
                ),
            ),
            pending=Count(
                "id",
                filter=Q(start_time__isnull=True),
            ),
        )

        total = stats["total"] or 0
        completed = stats["completed"] or 0

        completion_percentage = (
            round((completed / total) * 100, 2)
            if total > 0
            else 0.0
        )

        result = {
            "total_jobs": total,
            "completed_jobs": completed,
            "pending_jobs": stats["pending"] or 0,
            "running_jobs": stats["running"] or 0,
            "completion_percentage": completion_percentage,
            "average_tat": 0,
        }

        return result

    # _get_recent_work()
    def _get_recent_work(self, work):

        queryset = work.order_by("-id")[:10]

        recent = []

        for progress in queryset:

            job = progress.allocation.job

            recent.append(
                {
                    "id": job.id,
                    "job_no": job.job_no,
                    "claim_no": getattr(job, "claim_no", ""),
                    "vehicle_no": job.vehicle.registration_no,
                    "customer_name": job.vehicle.customer.name,
                    "advisor": (
                        job.advisor.name
                        if job.advisor
                        else ""
                    ),
                    "status": self._get_status(progress),
                }
            )

        return recent
    # _empty_dashboard()

    def _empty_dashboard(self):
        data = self._base_dashboard()
        data["dashboard_type"] = "default"
        return data

    # _empty_performance()
    def _empty_performance(self):
        return {
            "total_jobs": 0,
            "completed_jobs": 0,
            "pending_jobs": 0,
            "running_jobs": 0,
            "completion_percentage": 0,
            "average_tat": 0,
        }
    # _empty_Financial()
    def _empty_financial(self):
        return {
            "estimate": 0,
            "approved": 0,
            "invoice": 0,
            "collection": 0,
            "outstanding": 0,
            "average_job_value": 0,
            "gross_profit": 0,
            "net_profit": 0,
        }
