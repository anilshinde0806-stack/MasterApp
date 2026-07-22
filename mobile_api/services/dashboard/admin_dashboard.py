from .advisor_ranking_service import TopAdvisorService
from .base_dashboard import BaseDashboardService
from .admin_kpi_service import AdminKPIService
from .branch_performance_service import BranchPerformanceService
from .financial_service import FinancialService
from .revenue_service import RevenueService
from .technician_ranking_service import TopTechnicianService


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
            self.employee,
            self.branch,
        )

        top_advisors = TopAdvisorService(
            self.employee,
            self.branch,
        )

        top_technicians = TopTechnicianService(
            self.employee,
            self.branch,
        )

        branches = BranchPerformanceService(
            self.employee,
            self.branch,
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
