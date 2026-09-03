from django.db.models import (
    Count,
    Sum,
    DecimalField,
    Value,
    Q,
)
from django.db.models.functions import Coalesce

from core.models import Employee
from mobile_api.services.dashboard.filter_service import DashboardFilterService



class TopAdvisorService:

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


    def get(self):

        # ======================================
        # BASE ADVISORS
        # ======================================

        advisors = Employee.objects.filter(
            employee_type__iexact="Advisor",
            is_active=True,
        )


        # ======================================
        # BRANCH FILTER
        # ======================================

        if self.branch:

            advisors = advisors.filter(
                branch=self.branch
            )


        # ======================================
        # FILTER JOBCARDS BY PERIOD
        # ======================================

        from core.models import JobCard


        jobs = DashboardFilterService(
            queryset=JobCard.objects.all(),
            branch=self.branch,
            period=self.period,
            start_date=self.start_date,
            end_date=self.end_date,
            date_field="job_date",
        ).filter()


        # Get IDs of filtered jobs
        filtered_job_ids = jobs.values_list(
            "id",
            flat=True
        )


        # ======================================
        # ADVISOR PERFORMANCE
        # ======================================

        advisors = advisors.annotate(

            completed_jobs=Count(
                "advisor_jobs",
                filter=Q(
                    advisor_jobs__id__in=filtered_job_ids
                ),
                distinct=True,
            ),


            revenue=Coalesce(

                Sum(
                    "advisor_jobs__grand_total",

                    filter=Q(
                        advisor_jobs__id__in=filtered_job_ids
                    ),
                ),

                Value(
                    0,
                    output_field=DecimalField(
                        max_digits=14,
                        decimal_places=2,
                    ),
                ),

                output_field=DecimalField(
                    max_digits=14,
                    decimal_places=2,
                ),

            ),

        ).filter(

            # Don't show advisors with no jobs
            completed_jobs__gt=0

        ).order_by(

            "-revenue",
            "-completed_jobs"

        )[:5]


        # ======================================
        # RESPONSE
        # ======================================

        results = []

        for advisor in advisors:

            results.append({

                "id": advisor.id,

                "name": advisor.name,

                "completed_jobs": advisor.completed_jobs,

                "revenue": float(
                    advisor.revenue or 0
                ),

                "average_tat": 0,

                "rating": 0,

            })


        return results