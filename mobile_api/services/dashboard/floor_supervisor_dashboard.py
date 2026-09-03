from django.db.models import Q
from django.utils import timezone

from core.models import ClaimStageCode, JobCard

from .base_dashboard import BaseDashboardService


class FloorSupervisorDashboardService(BaseDashboardService):
    """Operational dashboard for a branch Floor Supervisor."""

    def __init__(self, user, branch=None):
        super().__init__(user)
        self.branch = branch or (self.employee.branch if self.employee else None)

    def get(self):
        jobs = JobCard.objects.select_related(
            "claim", "claim__vehicle", "claim__vehicle__customer", "advisor"
        )
        pending = jobs.filter(
            allocation__isnull=True,
            claim__claim_stage__gte=ClaimStageCode.WORK_ALLOCATION,
        ).exclude(repair_status__iexact="Closed").distinct()
        active = jobs.filter(
            allocation__isnull=False,
            allocation__progress__start_time__isnull=False,
            allocation__progress__finish_time__isnull=True,
            claim__claim_stage__gte=ClaimStageCode.REPAIR_IN_PROGRESS,
        ).distinct()
        approval = jobs.filter(
            additional_approval_required=True,
        ).filter(
            Q(second_approval_status__isnull=True)
            | Q(second_approval_status="")
            | Q(second_approval_status="Pending")
        )
        completed_today = jobs.filter(
            allocation__progress__finish_time__date=timezone.localdate(),
        ).distinct()

        total = pending.count() + active.count()
        completed = completed_today.count()
        return {
            "dashboard_type": "FLOOR_SUPERVISOR",
            "user": self._get_user(),
            "notification_count": self._get_notification_count(),
            "summaries": [
                {"title": "Pending Allocation", "value": pending.count(), "type": "allocation", "color": "#FB8C00", "icon": "assignment_ind"},
                {"title": "Repair Job Cards", "value": active.count(), "type": "repair", "color": "#00897B", "icon": "engineering"},
                {"title": "2nd Approval", "value": approval.count(), "type": "approval", "color": "#E53935", "icon": "approval"},
                {"title": "Completed Today", "value": completed, "type": "completed", "color": "#43A047", "icon": "check_circle"},
            ],
            "performance": {
                "total_jobs": total,
                "completed_jobs": completed,
                "pending_jobs": pending.count(),
                "running_jobs": active.count(),
                "completion_percentage": round(completed * 100 / total, 1) if total else 0,
                "average_tat": "0 Days",
            },
            "financial": self._empty_financial(),
            "actions": [
                {"id": 1, "title": "Work Allocation", "icon": "assignment_ind", "route": "/jobcards?queue=allocation", "color": "#FB8C00"},
                {"id": 2, "title": "Repair Progress", "icon": "engineering", "route": "/jobcards?queue=repair", "color": "#00897B"},
            ],
            "recent_work": self._recent_jobs(
                (pending | active).distinct()
            ),
            "pipeline": [
                {"title": "Pending Allocation", "count": pending.count(), "icon": "assignment_ind", "color": "#FB8C00"},
                {"title": "Repair Job Cards", "count": active.count(), "icon": "engineering", "color": "#00897B"},
                {"title": "Pending Approval", "count": approval.count(), "icon": "approval", "color": "#E53935"},
                {"title": "Completed Today", "count": completed, "icon": "check_circle", "color": "#43A047"},
            ],
        }

    @staticmethod
    def _recent_jobs(jobs):
        rows = []
        for job in jobs.order_by("-id")[:10]:
            vehicle = job.claim.vehicle if job.claim_id and job.claim.vehicle_id else job.vehicle
            customer = vehicle.customer if vehicle and vehicle.customer_id else None
            rows.append({
                "id": job.id,
                "job_no": job.job_no,
                "claim_no": job.claim.claim_no if job.claim_id else "",
                "vehicle_no": vehicle.registration_no if vehicle else "",
                "customer_name": customer.name if customer else "",
                "advisor": job.advisor.name if job.advisor_id else "",
                "status": job.repair_status,
            })
        return rows
