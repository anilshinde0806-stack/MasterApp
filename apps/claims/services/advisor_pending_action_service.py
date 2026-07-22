"""Shared pending-action read model for Advisor dashboards."""

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from core.models import ClaimStageCode


class AdvisorPendingActionService:
    """Derive actionable workflow gaps from already permission-scoped querysets.

    The service deliberately uses the presence/state of related records as well
    as ``claim_stage``.  This prevents a stale or prematurely advanced stage
    from hiding work that still needs to be completed.
    """

    CATEGORY_META = {
        "jobcard_pending": ("Job Card Pending", "Create a job card", "assignment", "danger"),
        "approval_pending": ("Insurance Approval", "Approval follow-up", "verified", "warning"),
        "allocation_pending": ("Work Allocation", "Allocate repair work", "engineering", "info"),
        "repair_not_started": ("Repair Not Started", "Start allocated work", "build", "warning"),
        "repair_followup": ("Repair Follow-up", "Repair is in progress", "engineering", "primary"),
        "closure_pending": ("Closure Pending", "Complete delivery and close", "task_alt", "success"),
    }

    def __init__(self, *, claims, jobcards, item_limit=25):
        self.claims = claims.select_related(
            "vehicle", "vehicle__customer", "employee", "branch"
        )
        self.jobcards = jobcards.select_related(
            "claim", "vehicle", "vehicle__customer", "advisor", "branch"
        ).prefetch_related("allocation__progress")
        self.item_limit = item_limit

    def get(self):
        items = []
        jobs_by_claim = {job.claim_id: job for job in self.jobcards if job.claim_id}

        for claim in self.claims.filter(status="Open").order_by("created_at"):
            job = jobs_by_claim.get(claim.id)
            action_type = self._claim_action(claim, job)
            if action_type:
                items.append(self._item(action_type, claim, job))

        # Include completed jobs whose claim queryset may exclude them because
        # the selected dashboard date is based on the job rather than claim.
        included_jobs = {item["job_id"] for item in items if item["job_id"]}
        for job in self.jobcards.order_by("created_at"):
            if job.id in included_jobs or not job.claim_id:
                continue
            if self._is_closure_pending(job.claim, job):
                items.append(self._item("closure_pending", job.claim, job))

        priority_order = {"high": 0, "medium": 1, "normal": 2}
        items.sort(key=lambda row: (priority_order[row["priority"]], -row["age_days"], row["claim_no"]))
        counts = {key: 0 for key in self.CATEGORY_META}
        for item in items:
            counts[item["type"]] += 1

        categories = []
        for key, (title, subtitle, icon, color) in self.CATEGORY_META.items():
            if counts[key]:
                categories.append({
                    "type": key,
                    "title": title,
                    "subtitle": subtitle,
                    "count": counts[key],
                    "icon": icon,
                    "color": color,
                    "desktop_url": self._category_desktop_url(key),
                    "route": self._category_route(key),
                })

        return {
            "total": len(items),
            "categories": categories,
            "items": items[: self.item_limit],
        }

    @staticmethod
    def _category_desktop_url(action_type):
        if action_type in {"jobcard_pending", "approval_pending"}:
            return "/claimList/"
        if action_type in {"allocation_pending", "repair_not_started"}:
            return "/work-allocation/"
        return "/jobList/"

    @staticmethod
    def _category_route(action_type):
        if action_type in {"jobcard_pending", "approval_pending"}:
            return "claims"
        if action_type in {"allocation_pending", "repair_not_started"}:
            return "allocation"
        if action_type == "repair_followup":
            return "repair"
        return "delivery"

    def _claim_action(self, claim, job):
        if job is None:
            return "jobcard_pending"
        if self._is_closure_pending(claim, job):
            return "closure_pending"
        if not claim.insurance_approval_date or claim.claim_stage <= ClaimStageCode.INSURANCE_APPROVAL:
            return "approval_pending"
        try:
            allocation = job.allocation
        except ObjectDoesNotExist:
            return "allocation_pending"
        progress = list(allocation.progress.all())
        if not progress or not any(row.start_time for row in progress):
            return "repair_not_started"
        if any(row.start_time and not row.finish_time for row in progress):
            return "repair_followup"
        if progress and all(row.finish_time for row in progress):
            return "closure_pending"
        return None

    @staticmethod
    def _is_closure_pending(claim, job):
        repair_done = job.repair_status == "Completed" or claim.claim_stage >= ClaimStageCode.WORK_COMPLETED
        return repair_done and claim.status != "Closed"

    def _item(self, action_type, claim, job):
        title, subtitle, icon, color = self.CATEGORY_META[action_type]
        created_at = job.created_at if job and getattr(job, "created_at", None) else claim.created_at
        age_days = max((timezone.localdate() - timezone.localtime(created_at).date()).days, 0)
        vehicle = job.vehicle if job and job.vehicle_id else claim.vehicle
        customer = vehicle.customer if vehicle and vehicle.customer_id else None
        priority = "high" if age_days >= 3 else "medium" if age_days >= 1 else "normal"
        return {
            "type": action_type,
            "title": title,
            "subtitle": subtitle,
            "icon": icon,
            "color": color,
            "claim_id": claim.id,
            "claim_no": claim.claim_no,
            "job_id": job.id if job else None,
            "job_no": job.job_no if job else "",
            "vehicle_no": vehicle.registration_no if vehicle else "",
            "customer_name": customer.name if customer else "",
            "stage": claim.get_claim_stage_display(),
            "age_days": age_days,
            "priority": priority,
            "desktop_url": (
                f"/work-allocation/{job.id}/" if action_type == "allocation_pending" and job
                else f"/jobCard/{job.id}/edit/" if job
                else f"/claim/{claim.id}/edit/"
            ),
            "route": f"/jobcards/{job.id}" if job else f"/claims/{claim.id}",
        }
