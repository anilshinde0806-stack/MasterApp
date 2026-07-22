"""Shared Advisor dashboard read model for desktop presentation."""

from django.db.models import Count, Q

from core.models import ClaimStageCode, WorkProgress
from .advisor_pending_action_service import AdvisorPendingActionService


class AdvisorDashboardReadService:
    def __init__(self, *, claims, jobcards):
        self.claims = claims
        self.jobcards = jobcards
        self.work = WorkProgress.objects.filter(
            allocation__job__in=jobcards,
        ).select_related(
            "allocation__job",
            "allocation__job__claim",
            "allocation__job__vehicle",
            "allocation__job__vehicle__customer",
            "allocation__job__advisor",
            "employee",
        ).prefetch_related("allocation__progress__photos")

    def get(self):
        pending_actions = AdvisorPendingActionService(
            claims=self.claims,
            jobcards=self.jobcards,
        ).get()
        return {
            "summaries": self._summaries(),
            "pipeline": self._pipeline(),
            "performance": self._performance(),
            "recent_work": self._recent_work(),
            "pending_actions": pending_actions,
        }

    def _summaries(self):
        return [
            {"title": "Assigned", "value": self.jobcards.filter(repair_status="Open").count(), "color": "primary"},
            {"title": "Survey", "value": self.claims.filter(claim_stage=ClaimStageCode.SURVEY).count(), "color": "info"},
            {"title": "Approval", "value": self.claims.filter(claim_stage=ClaimStageCode.INSURANCE_APPROVAL).count(), "color": "warning"},
            {"title": "Repair", "value": self.claims.filter(claim_stage=ClaimStageCode.REPAIR_IN_PROGRESS).count(), "color": "success"},
            {"title": "Ready", "value": self.jobcards.filter(ready_for_delivery=True).count(), "color": "secondary"},
            {"title": "Delivered", "value": self.jobcards.filter(repair_status="Closed").count(), "color": "success"},
        ]

    def _pipeline(self):
        counts = {
            item["claim_stage"]: item["total"]
            for item in self.claims.values("claim_stage").annotate(total=Count("id"))
        }
        return [
            {"title": "Survey", "count": counts.get(ClaimStageCode.SURVEY, 0), "color": "info"},
            {"title": "Approval", "count": counts.get(ClaimStageCode.INSURANCE_APPROVAL, 0), "color": "warning"},
            {"title": "Repair", "count": counts.get(ClaimStageCode.REPAIR_IN_PROGRESS, 0), "color": "success"},
            {"title": "Delivery", "count": sum(counts.get(stage, 0) for stage in range(ClaimStageCode.WORK_COMPLETED, ClaimStageCode.CLOSED)), "color": "primary"},
        ]

    def _performance(self):
        stats = self.work.aggregate(
            total=Count("id"),
            completed=Count("id", filter=Q(finish_time__isnull=False)),
            running=Count("id", filter=Q(start_time__isnull=False, finish_time__isnull=True)),
            pending=Count("id", filter=Q(start_time__isnull=True)),
        )
        total = stats["total"] or 0
        completed = stats["completed"] or 0
        return {
            **stats,
            "completion_percentage": round(completed * 100 / total, 1) if total else 0,
        }

    def _recent_work(self):
        rows = []
        seen = set()
        for item in self.work.order_by("-id")[:50]:
            if item.allocation_id in seen:
                continue
            seen.add(item.allocation_id)
            job = item.allocation.job
            progress_rows = list(item.allocation.progress.all())
            total = len(progress_rows)
            completed = sum(1 for row in progress_rows if row.finish_time)
            running = sum(1 for row in progress_rows if row.start_time and not row.finish_time)
            progress = (completed + running * 0.5) / total if total else 0
            if job.repair_status in {"Completed", "Closed"}:
                progress = 1
            rows.append({
                "job_id": job.id,
                "job_no": job.job_no,
                "claim_no": job.claim.claim_no if job.claim_id else "",
                "vehicle_no": job.vehicle.registration_no if job.vehicle_id else "",
                "customer_name": job.vehicle.customer.name if job.vehicle_id and job.vehicle.customer_id else "",
                "technician": item.employee.name if item.employee_id else "-",
                "status": job.repair_status,
                "progress": round(progress * 100),
                "photo_count": sum(len(row.photos.all()) for row in progress_rows),
            })
            if len(rows) >= 10:
                break
        return rows
