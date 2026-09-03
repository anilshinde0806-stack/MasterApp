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

class AdminDashboardService(BaseDashboardService):

    def __init__(self, user, employee=None, branch=None, period="today", start_date=None, end_date=None):
        super().__init__(user, branch, employee=employee)
        self.user = user

        self.branch = branch
        self.period = period

        self.start_date = start_date
        self.end_date = end_date

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

            "actions": [],

            "recent_work": [],
        })

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