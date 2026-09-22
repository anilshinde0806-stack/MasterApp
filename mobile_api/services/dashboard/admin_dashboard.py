from apps import workshop
from apps.claims.services.jobcard_pipeline_service import JobcardPipelineService

from .advisor_ranking_service import TopAdvisorService
from .base_dashboard import BaseDashboardService
from .admin_kpi_service import AdminKPIService
from .branch_performance_service import BranchPerformanceService
from .financial_service import FinancialService
from .revenue_service import RevenueService
from .technician_ranking_service import TopTechnicianService
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from mobile_api.services.dashboard.workshop_performance_service import (
    WorkshopPerformanceService
)

class AdminDashboardService(BaseDashboardService):

    def __init__(self, user, employee=None, branch=None, period="today", start_date=None, end_date=None):
        super().__init__(user, branch, employee=employee)
        self.user = user

        self.branch = branch
        self.period = period

        self.start_date = start_date
        self.end_date = end_date
        self._resolve_period_dates()

    def _resolve_period_dates(self):

        today = timezone.localdate()


        # =====================================
        # TODAY
        # =====================================

        if self.period == "today":

            self.start_date = today
            self.end_date = today

            return


        # =====================================
        # YESTERDAY
        # =====================================

        if self.period == "yesterday":

            yesterday = today - timedelta(days=1)

            self.start_date = yesterday
            self.end_date = yesterday

            return


        # =====================================
        # THIS WEEK
        # =====================================

        if self.period == "this_week":

            self.start_date = today - timedelta(
                days=today.weekday()
            )

            self.end_date = today

            return


        # =====================================
        # THIS MONTH
        # =====================================

        if self.period == "this_month":

            self.start_date = today.replace(day=1)

            self.end_date = today

            return


        # =====================================
        # LAST MONTH
        # =====================================

        if self.period == "last_month":

            first_day_this_month = today.replace(day=1)

            last_day_last_month = (
                first_day_this_month
                - timedelta(days=1)
            )

            self.start_date = last_day_last_month.replace(
                day=1
            )

            self.end_date = last_day_last_month

            return


        # =====================================
        # THIS YEAR
        # =====================================

        if self.period == "this_year":

            self.start_date = today.replace(
                month=1,
                day=1,
            )

            self.end_date = today

            return


        # =====================================
        # CUSTOM
        # =====================================

        # Keep user-provided dates unchanged
        if self.period == "custom":

            return


        # =====================================
        # ALL / DEFAULT
        # =====================================

        self.start_date = None
        self.end_date = None
    def get(self):

        work = self._get_work_queryset(
            self.employee,
            self.branch,
        )

        # Apply period/date filters
        work = self._filter_work_by_period(work)
        kpi = AdminKPIService(
            employee=self.employee,
            branch=self.branch,
            period=self.period,
            start_date=self.start_date,
            end_date=self.end_date,
        )
        data = self._base_dashboard()
        financial = FinancialService(
            self.employee,
            self.branch,
            period=self.period,
            start_date=self.start_date,
            end_date=self.end_date,
        )

        revenue = RevenueService(
        employee=self.employee,
        branch=self.branch,
        period=self.period,
        start_date=self.start_date,
        end_date=self.end_date,
        )

        top_advisors = TopAdvisorService(
            employee=self.employee,
            branch=self.branch,
            period=self.period,
            start_date=self.start_date,
            end_date=self.end_date,
        )


        top_technicians = TopTechnicianService(
            employee=self.employee,
            branch=self.branch,
            period=self.period,
            start_date=self.start_date,
            end_date=self.end_date,
        )


        branches = BranchPerformanceService(
            employee=self.employee,
            branch=self.branch,
            period=self.period,
            start_date=self.start_date,
            end_date=self.end_date,
        )

        workshop = WorkshopPerformanceService(jobcards=work)
     

        # ==========================================
        # WORKSHOP DASHBOARD
        # ==========================================

        workshop_data = workshop.get()

        print("\n========== WORKSHOP DASHBOARD DEBUG ==========")

        print(workshop_data)

        print("==============================================\n")

        jobcard_data = JobcardPipelineService(
            branch=self.branch,
            start_date=self.start_date,
            end_date=self.end_date,
        ).get()

        print("\n========== RAW JOBCARD DATA ==========")
        print(jobcard_data)
        print("TYPE:", type(jobcard_data))
        print("PIPELINE:", jobcard_data.get("pipeline", []))
        print("======================================\n")
        data.update({
            "dashboard_type": "ADMIN",

            "summaries": kpi.get_summaries(),

            "performance": self._get_performance(work),

            "financial": financial.get(),

            "revenue": revenue.get(),

            "top_advisors": top_advisors.get(),

            "top_technicians": top_technicians.get(),

            "branch_performance": branches.get(),

            "pipeline": kpi._get_pipeline(),
            "workshop_dashboard": workshop_data,
            "jobcard_pipeline": jobcard_data.get(
                        "pipeline",
                        []
                    ),
            "actions": [],

            "recent_work": [],
        })

        
        print("\n========== FINAL ADMIN DASHBOARD KEYS ==========")

        print(data.keys())

        print("\nHAS WORKSHOP DASHBOARD:")

        print("workshop_dashboard" in data)
        print("HAS JOBCARD PIPELINE:")
        print(jobcard_data.get(
                        "pipeline",
                        []
                    ))
        print("===============================================\n")

        return data
    def _filter_work_by_period(self, work):

        today = timezone.localdate()

        date_field = "allocation__job__job_date__date"


        if self.period == "today":

            return work.filter(
                **{
                    date_field: today
                }
            )


        if self.period == "yesterday":

            return work.filter(
                **{
                    date_field:
                        today - timedelta(days=1)
                }
            )


        if self.period == "this_week":

            start = today - timedelta(
                days=today.weekday()
            )

            return work.filter(
                **{
                    f"{date_field}__range":
                        [start, today]
                }
            )


        if self.period == "this_month":

            return work.filter(
                allocation__job__job_date__year=today.year,
                allocation__job__job_date__month=today.month,
            )


        if self.period == "last_month":

            first = today.replace(day=1)

            last_month = (
                first - timedelta(days=1)
            )

            return work.filter(
                allocation__job__job_date__year=
                    last_month.year,

                allocation__job__job_date__month=
                    last_month.month,
            )


        if self.period == "this_year":

            return work.filter(
                allocation__job__job_date__year=
                    today.year
            )


        if (
            self.period == "custom"
            and self.start_date
            and self.end_date
        ):

            return work.filter(
                allocation__job__job_date__date__range=[
                    self.start_date,
                    self.end_date,
                ]
            )


        return work