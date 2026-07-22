from django.db.models import Count

from core.models import Claim, ClaimStageCode
from mobile_api.utils.branch_filter import filter_branch
from mobile_api.services.dashboard.filter_service import DashboardFilterService


class AdvisorPipelineService:

    def __init__(self, employee, branch, period=None, start_date=None, end_date=None):

        self.employee = employee
        self.branch = branch
        self.period = period
        self.start_date = start_date
        self.end_date = end_date

    def get(self):

        claims = filter_branch(
            Claim.objects.filter(
                employee=self.employee
            ),
            self.branch,
        )
        claims = DashboardFilterService(
            queryset=claims,
            period=self.period,
            start_date=self.start_date,
            end_date=self.end_date,
        ).filter()

        stats = (
            claims
            .values("claim_stage")
            .annotate(total=Count("id"))
        )

        counts = {
            item["claim_stage"]: item["total"]
            for item in stats
        }

        return [
            {
                "stage": 1,
                "title": "Survey",
                "count": counts.get(ClaimStageCode.SURVEY, 0),
                "icon": "camera_alt",
                "color": "#29B6F6",
            },
            {
                "stage": 2,
                "title": "Approval",
                "count": counts.get(ClaimStageCode.INSURANCE_APPROVAL, 0),
                "icon": "verified",
                "color": "#FFA726",
            },
            {
                "stage": 3,
                "title": "Repair",
                "count": counts.get(ClaimStageCode.REPAIR_IN_PROGRESS, 0),
                "icon": "engineering",
                "color": "#26A69A",
            },
            {
                "stage": 4,
                "title": "Delivery",
                "count": counts.get(ClaimStageCode.WORK_COMPLETED, 0),
                "icon": "local_shipping",
                "color": "#66BB6A",
            },
        ]
