from .advisor_kpi import AdvisorKPIService
from .advisor_pipeline import AdvisorPipelineService
from .advisor_performance import AdvisorPerformanceService
from .advisor_recent import AdvisorRecentWorkService
from .advisor_followup import AdvisorFollowupService
from .base_dashboard import BaseDashboardService
from apps.claims.services.advisor_pending_action_service import AdvisorPendingActionService
from core.models import Claim, JobCard
from mobile_api.utils.branch_filter import filter_branch
from mobile_api.services.dashboard.filter_service import DashboardFilterService

class AdvisorDashboardService(BaseDashboardService):

    def __init__(self, user, employee=None, branch=None, period="today", start_date=None, end_date=None):
        super().__init__(user, branch, employee=employee)
        self.period = period
        self.start_date = start_date
        self.end_date = end_date

    def get(self):

        work = self._get_work_queryset(
            self.employee,
            self.branch,
        )

        claims = Claim.objects.filter(employee=self.employee)
        jobs = JobCard.objects.filter(advisor=self.employee)
        claims = DashboardFilterService(
            filter_branch(claims, self.branch),
            period=self.period,
            start_date=self.start_date,
            end_date=self.end_date,
        ).filter()
        jobs = DashboardFilterService(
            filter_branch(jobs, self.branch),
            period=self.period,
            start_date=self.start_date,
            end_date=self.end_date,
        ).filter()
        pending_actions = AdvisorPendingActionService(
            claims=claims,
            jobcards=jobs,
        ).get()

        return {
            "dashboard_type": "ADVISOR",

            "user": self._get_user(),

            "summaries": AdvisorKPIService(
                self.employee,
                self.branch,
                period=self.period,
                start_date=self.start_date,
                end_date=self.end_date,
            ).get(),

            "performance": AdvisorPerformanceService(
                work,
            ).get(),

            "financial": self._empty_financial(),

            "pipeline": AdvisorPipelineService(
                self.employee,
                self.branch,
                period=self.period,
                start_date=self.start_date,
                end_date=self.end_date,
            ).get(),

            "recent_work": AdvisorRecentWorkService(
                work,
            ).get(),

            "followups": AdvisorFollowupService(
                self.employee,
                self.branch,
            ).get(),

            "pending_actions": pending_actions,

            "actions": self._get_actions(
                self.employee,
            ),
            "notification_count": self._get_notification_count(),
        }
