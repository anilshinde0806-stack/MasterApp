"""Shared database-backed Admin dashboard KPIs."""

from django.db.models import Count

from apps.claims.repositories.dashboard_repository import DashboardKPIRepository
from core.models import ClaimStageCode


class DashboardKPIService:
    def __init__(self, *, claims, jobcards):
        self.claims = claims
        self.jobcards = jobcards

    def get(self):
        if DashboardKPIRepository.is_available():
            return DashboardKPIRepository.get(
                claim_ids=self.claims.values_list("pk", flat=True),
                jobcard_ids=self.jobcards.values_list("pk", flat=True),
            )
        return self._get_with_orm()

    def _get_with_orm(self):
        open_claims = self.claims.filter(status="Open")
        open_jobs = self.jobcards.filter(repair_status="Open")
        stage_counts = open_claims.values("claim_stage").annotate(total=Count("id"))
        return {
            "open_claims": open_claims.count(),
            "open_jobcards": open_jobs.count(),
            "workshop": open_jobs.count(),
            "insurance": open_claims.filter(
                claim_stage=ClaimStageCode.INSURANCE_APPROVAL
            ).count(),
            "survey": open_claims.filter(claim_stage=ClaimStageCode.SURVEY).count(),
            "delivery": self.jobcards.filter(ready_for_delivery=True).count(),
            "pipeline_counts": {
                str(item["claim_stage"]): item["total"] for item in stage_counts
            },
        }
