from core.models import WorkProgress

from .base_dashboard import BaseDashboardService


class TechnicianDashboardService(BaseDashboardService):
    """Dashboard for technicians, painters, and denters."""

    def get(self):
        work = (
            WorkProgress.objects
            .select_related(
                "allocation__job__advisor",
                "allocation__job__claim__vehicle__customer",
                "allocation__job__vehicle__customer",
            )
            .prefetch_related("photos")
            .filter(employee=self.employee)
        )

        data = self._base_dashboard()
        data.update(
            {
                "dashboard_type": "TECHNICIAN",
                "summaries": self._get_summaries(work),
                "performance": self._get_performance(work),
                "actions": [
                    {
                        "id": 1,
                        "title": "My Work",
                        "icon": "engineering",
                        "route": "/my-work",
                        "color": "#1976D2",
                    }
                ],
                "recent_work": self._recent_work(work),
            }
        )
        return data

    def _recent_work(self, work):
        rows = []
        for progress in work.order_by("-id")[:10]:
            job = progress.allocation.job
            claim = job.claim if job.claim_id else None
            vehicle = claim.vehicle if claim and claim.vehicle_id else job.vehicle
            customer = vehicle.customer if vehicle and vehicle.customer_id else None

            rows.append(
                {
                    "id": job.id,
                    "progress_id": progress.id,
                    "job_no": job.job_no or "",
                    "claim_no": claim.claim_no if claim else "",
                    "vehicle_no": vehicle.registration_no if vehicle else "",
                    "customer_name": customer.name if customer else "",
                    "advisor": job.advisor.name if job.advisor else "",
                    "technician": self.employee.name if self.employee else "",
                    "status": self._get_status(progress),
                    "photo_count": len(progress.photos.all()),
                    "remarks_added": bool(progress.remarks),
                    "updated_at": (
                        progress.finish_time or progress.start_time
                    ).isoformat() if progress.finish_time or progress.start_time else "",
                }
            )
        return rows
