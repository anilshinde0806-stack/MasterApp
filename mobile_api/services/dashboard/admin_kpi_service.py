from mobile_api.services.dashboard.filter_service import DashboardFilterService
from apps.claims.services.dashboard_kpi_service import DashboardKPIService
from core.models import (
    Claim,
    JobCard,
    ClaimStageCode
)



class AdminKPIService:

    def __init__(
        self,
        employee,
        branch=None,
        period="today",
        start_date=None,
        end_date=None,
    ):

        self.employee = employee
        self.branch = branch
        self.period = period
        self.start_date = start_date
        self.end_date = end_date


        # =====================================
        # CLAIMS
        # =====================================

        claims_queryset = Claim.objects.select_related(
            "jobcard",
            "jobcard__branch",
            "insurance_company",
        )

        print("\n========== CLAIM DEBUG ==========")
        print("Before filter:", claims_queryset.count())
        print("Start date:", self.start_date)
        print("End date:", self.end_date)

        self.claims = DashboardFilterService(
            queryset=claims_queryset,
            branch=self.branch,
            period=self.period,
            start_date=self.start_date,
            end_date=self.end_date,
            date_field="created_at",
        ).filter()

        print("After filter:", self.claims.count())
        print("=================================\n")


        # =====================================
        # JOBCARDS
        # =====================================

        jobcards_queryset = JobCard.objects.select_related(
            "branch",
        )

        print("\n========== JOBCARD DEBUG ==========")
        print("Before filter:", jobcards_queryset.count())

        self.jobcards = DashboardFilterService(
            queryset=jobcards_queryset,
            branch=self.branch,
            period=self.period,
            start_date=self.start_date,
            end_date=self.end_date,
            date_field="job_date",
        ).filter()

        print("After filter:", self.jobcards.count())
        print("===================================\n")


        self._metrics = None

    def _get_metrics(self):
        if self._metrics is None:
            self._metrics = DashboardKPIService(
                claims=self.claims,
                jobcards=self.jobcards,
            ).get()
        print("\n========== FINAL KPI METRICS ==========")
        print(self._metrics)
        print("=======================================\n")
    
        return self._metrics


    def get_summaries(self):
        metrics = self._get_metrics()
        claims = metrics["open_claims"]
        jobcards = metrics["open_jobcards"]
        workshop = metrics["workshop"]
        insurance = metrics["insurance"]
        survey = metrics["survey"]
        delivery = metrics["delivery"]

        return [

            {
                "title": "Claims",
                "value": claims,
                "subtitle": "Open Claims",
                "type": "claims",
                "icon": "description",
                "color": "#1976D2",
            },

            {
                "title": "Job Cards",
                "value": jobcards,
                "subtitle": "Open Jobs",
                "type": "jobcards",
                "icon": "engineering",
                "color": "#00897B",
            },

            {
                "title": "Workshop",
                "value": workshop,
                "subtitle": "In Repair",
                "type": "workshop",
                "icon": "directions_car",
                "color": "#FB8C00",
            },

            {
                "title": "Insurance",
                "value": insurance,
                "subtitle": "Pending",
                "type": "insurance",
                "icon": "verified",
                "color": "#E53935",
            },

            {
                "title": "Survey",
                "value": survey,
                "subtitle": "Pending",
                "type": "survey",
                "icon": "camera_alt",
                "color": "#00ACC1",
            },

            {
                "title": "Delivery",
                "value": delivery,
                "subtitle": "Ready",
                "type": "delivery",
                "icon": "local_shipping",
                "color": "#8E24AA",
            },
        ]



    def _get_pipeline(self):

        counts = {
            int(stage): total
            for stage, total in self._get_metrics()
            .get("pipeline_counts", {})
            .items()
        }

        return [

        {
            "stage": ClaimStageCode.CLAIM_CREATED,
            "title": "Claim Created",
            "count": counts.get(
                ClaimStageCode.CLAIM_CREATED, 0
            ),
            "icon": "description",
            "color": "#1976D2",
        },

        {
            "stage": ClaimStageCode.ADVISOR_ASSIGNED,
            "title": "Advisor Assigned",
            "count": counts.get(
                ClaimStageCode.ADVISOR_ASSIGNED, 0
            ),
            "icon": "person",
            "color": "#3949AB",
        },

        {
            "stage": ClaimStageCode.ESTIMATE_CREATED,
            "title": "Estimate Created",
            "count": counts.get(
                ClaimStageCode.ESTIMATE_CREATED, 0
            ),
            "icon": "request_quote",
            "color": "#0891B2",
        },

        {
            "stage": ClaimStageCode.INTIMATION,
            "title": "Claim Intimation",
            "count": counts.get(
                ClaimStageCode.INTIMATION, 0
            ),
            "icon": "notifications",
            "color": "#F59E0B",
        },

        {
            "stage": ClaimStageCode.SURVEY,
            "title": "Survey Done",
            "count": counts.get(
                ClaimStageCode.SURVEY, 0
            ),
            "icon": "camera_alt",
            "color": "#06B6D4",
        },

        {
            "stage": ClaimStageCode.INSURANCE_APPROVAL,
            "title": "Insurance Approval",
            "count": counts.get(
                ClaimStageCode.INSURANCE_APPROVAL, 0
            ),
            "icon": "verified",
            "color": "#16A34A",
        },

        {
            "stage": ClaimStageCode.WORK_ALLOCATION,
            "title": "Work Allocation Pending",
            "count": counts.get(
                ClaimStageCode.WORK_ALLOCATION, 0
            ),
            "icon": "engineering",
            "color": "#F97316",
        },

        {
            "stage": ClaimStageCode.REPAIR_IN_PROGRESS,
            "title": "Repair Work In Progress",
            "count": counts.get(
                ClaimStageCode.REPAIR_IN_PROGRESS, 0
            ),
            "icon": "build",
            "color": "#8B5CF6",
        },

        {
            "stage": ClaimStageCode.WORK_COMPLETED,
            "title": "Work Completed",
            "count": counts.get(
                ClaimStageCode.WORK_COMPLETED, 0
            ),
            "icon": "check_circle",
            "color": "#22C55E",
        },

        {
            "stage": ClaimStageCode.RE_INSPECTION,
            "title": "Re Inspection",
            "count": counts.get(
                ClaimStageCode.RE_INSPECTION, 0
            ),
            "icon": "search",
            "color": "#EC4899",
        },

        {
            "stage": ClaimStageCode.LIABILITY,
            "title": "Liability",
            "count": counts.get(
                ClaimStageCode.LIABILITY, 0
            ),
            "icon": "scale",
            "color": "#64748B",
        },

        {
            "stage": ClaimStageCode.INVOICED,
            "title": "Invoiced",
            "count": counts.get(
                ClaimStageCode.INVOICED, 0
            ),
            "icon": "receipt",
            "color": "#14B8A6",
        },

        {
            "stage": ClaimStageCode.DELIVERY,
            "title": "Delivery",
            "count": counts.get(
                ClaimStageCode.DELIVERY, 0
            ),
            "icon": "local_shipping",
            "color": "#3B82F6",
        },

        {
            "stage": ClaimStageCode.CLOSED,
            "title": "Closed",
            "count": counts.get(
                ClaimStageCode.CLOSED, 0
            ),
            "icon": "lock",
            "color": "#475569",
        },

    ]