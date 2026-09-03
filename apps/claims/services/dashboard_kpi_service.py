"""Shared database-backed Admin dashboard KPIs."""

from django.db.models import Count

from apps.claims.repositories.dashboard_repository import DashboardKPIRepository
from core.models import ClaimStageCode


class DashboardKPIService:

    def __init__(self, *, claims, jobcards):
        self.claims = claims
        self.jobcards = jobcards

    def get(self):

        print("========== DASHBOARD KPI DEBUG ==========")

        print("TOTAL CLAIMS:", self.claims.count())
        print("TOTAL JOBCARDS:", self.jobcards.count())

        print(
            "OPEN CLAIMS:",
            self.claims.filter(status="Open").count()
        )

        print(
            "OPEN JOBS:",
            self.jobcards.filter(
                repair_status="Open"
            ).count()
        )

        print("========================================")

        if DashboardKPIRepository.is_available():

            return DashboardKPIRepository.get(
                claim_ids=self.claims.values_list(
                    "pk",
                    flat=True
                ),
                jobcard_ids=self.jobcards.values_list(
                    "pk",
                    flat=True
                ),
            )

        return self._get_with_orm()
