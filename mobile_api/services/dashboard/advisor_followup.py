from django.db.models import Count

from core.models import (
    Claim,
    JobCard,
    ClaimStageCode,
)

from mobile_api.utils.branch_filter import filter_branch


class AdvisorFollowupService:

    def __init__(self, employee, branch=None):
        self.employee = employee
        self.branch = branch

    def get(self):

        claims = filter_branch(
            Claim.objects.filter(
                employee=self.employee,
                status="Open",
            ),
            self.branch,
        )

        jobs = filter_branch(
            JobCard.objects.filter(
                advisor=self.employee,
            ),
            self.branch,
        )

        insurance_pending = claims.filter(
            claim_stage=ClaimStageCode.INSURANCE_APPROVAL
        ).count()

        survey_pending = claims.filter(
            claim_stage=ClaimStageCode.SURVEY
        ).count()

        ready_delivery = jobs.filter(
            ready_for_delivery=True
        ).count()

        running_repairs = jobs.filter(
            repair_status="Open"
        ).count()

        return [

            {
                "title": "Insurance Approval",
                "subtitle": "Follow-up Required",
                "count": insurance_pending,
                "icon": "verified",
                "color": "#FB8C00",
                "route": "/claims",
            },

            {
                "title": "Survey Pending",
                "subtitle": "Surveyor Visit",
                "count": survey_pending,
                "icon": "camera_alt",
                "color": "#00ACC1",
                "route": "/claims",
            },

            {
                "title": "Repair Running",
                "subtitle": "Workshop",
                "count": running_repairs,
                "icon": "engineering",
                "color": "#00897B",
                "route": "/jobcards",
            },

            {
                "title": "Ready Delivery",
                "subtitle": "Customer Call",
                "count": ready_delivery,
                "icon": "local_shipping",
                "color": "#43A047",
                "route": "/delivery",
            },

        ]