from django.db.models import Count, Q
from core.models import Claim, JobCard, ClaimStageCode
from mobile_api.utils.branch_filter import filter_branch
from mobile_api.services.dashboard.filter_service import DashboardFilterService


class AdvisorKPIService:

    def __init__(self, employee, branch=None, period=None, start_date=None, end_date=None):
        self.employee = employee
        self.branch = branch
        self.period = period
        self.start_date = start_date
        self.end_date = end_date

    def _for_period(self, queryset):
        return DashboardFilterService(
            queryset=queryset,
            period=self.period,
            start_date=self.start_date,
            end_date=self.end_date,
        ).filter()

    def _claims(self):
        qs = Claim.objects.filter(employee=self.employee)
        return self._for_period(filter_branch(qs, self.branch))

    def _jobcards(self):
        qs = JobCard.objects.filter(advisor=self.employee)
        return self._for_period(filter_branch(qs, self.branch))

    def get(self):

        claims = self._claims()
        jobs = self._jobcards()

        assigned = jobs.filter(
            repair_status="Open"
        ).count()

        survey = claims.filter(
            claim_stage=ClaimStageCode.SURVEY
        ).count()

        approval = claims.filter(
            claim_stage=ClaimStageCode.INSURANCE_APPROVAL
        ).count()

        repair = jobs.filter(
            repair_status="Repair"
        ).count()

        ready = jobs.filter(
            ready_for_delivery=True
        ).count()

        delivered = jobs.filter(
            repair_status="Closed"
        ).count()

        return [
            {
                "title": "Assigned",
                "value": assigned,
                "type": "assigned",
                "icon": "assignment",
                "color": "#1976D2",
            },
            {
                "title": "Survey",
                "value": survey,
                "type": "survey",
                "icon": "camera_alt",
                "color": "#00ACC1",
            },
            {
                "title": "Approval",
                "value": approval,
                "type": "approval",
                "icon": "verified",
                "color": "#FB8C00",
            },
            {
                "title": "Repair",
                "value": repair,
                "type": "repair",
                "icon": "engineering",
                "color": "#00897B",
            },
            {
                "title": "Ready",
                "value": ready,
                "type": "ready",
                "icon": "local_shipping",
                "color": "#8E24AA",
            },
            {
                "title": "Delivered",
                "value": delivered,
                "type": "delivered",
                "icon": "check_circle",
                "color": "#43A047",
            },
        ]
