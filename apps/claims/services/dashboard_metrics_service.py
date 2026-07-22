"""Manager dashboard metrics shared independently of presentation."""

from django.db.models import Count, Q, Sum

from apps.claims.repositories.dashboard_repository import DashboardMetricsRepository
from core.models import Claim, ClaimStageCode


class DashboardMetricsService:
    def __init__(self, *, claims, period_claims, jobcards, start_date, end_date):
        self.claims = claims
        self.period_claims = period_claims
        self.jobcards = jobcards
        self.start_date = start_date
        self.end_date = end_date

    def get(self):
        if DashboardMetricsRepository.is_available():
            values = DashboardMetricsRepository.get(
                claim_ids=self.claims.values_list("pk", flat=True),
                period_claim_ids=self.period_claims.values_list("pk", flat=True),
                jobcard_ids=self.jobcards.values_list("pk", flat=True),
                start_date=self.start_date,
                end_date=self.end_date,
            )
            return {
                "total_claims": values.get("total_claims", 0),
                "pending_claims": values.get("pending_claims", 0),
                "closed_claims": values.get("closed_claims", 0),
                "work_allocation_pending": values.get("work_allocation_pending", 0),
                "repair_in_progress": values.get("repair_in_progress", 0),
                "stage_counts": values.get("stage_counts") or [],
                "advisor_counts": values.get("advisor_counts") or [],
                "total_estimate_value": values.get("total_estimate_value") or 0,
            }
        return self._get_with_orm()

    def _get_with_orm(self):
        open_claims = self.claims.filter(created_at__date__lte=self.end_date).exclude(
            Q(claim_stage=ClaimStageCode.CLOSED)
            | Q(status__iexact="Closed")
            | Q(status__iexact="Cancelled")
        )
        closed = self.claims.filter(
            Q(claim_stage=ClaimStageCode.CLOSED) | Q(status__iexact="Closed")
        ).filter(
            Q(delivery_datetime__date__range=(self.start_date, self.end_date))
            | Q(
                delivery_datetime__isnull=True,
                updated_at__date__range=(self.start_date, self.end_date),
            )
        )
        pending = open_claims.count()
        closed_count = closed.count()
        return {
            "total_claims": pending + closed_count,
            "pending_claims": pending,
            "closed_claims": closed_count,
            "work_allocation_pending": open_claims.filter(
                claim_stage=ClaimStageCode.WORK_ALLOCATION
            ).count(),
            "repair_in_progress": open_claims.filter(
                claim_stage=ClaimStageCode.REPAIR_IN_PROGRESS
            ).count(),
            "stage_counts": list(
                self.period_claims.values("claim_stage")
                .annotate(total=Count("id"))
                .order_by("claim_stage")
            ),
            "advisor_counts": list(
                self.period_claims.values(
                    "employee__name", "employee__branch__code", "employee__branch__name"
                ).annotate(total=Count("id")).order_by("-total")[:10]
            ),
            "total_estimate_value": self.jobcards.aggregate(total=Sum("grand_total"))["total"] or 0,
        }
