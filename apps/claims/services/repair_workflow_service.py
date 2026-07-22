"""Claim-stage gate for allocation and repair progress operations."""

from core.models import ClaimStageCode


class RepairWorkflowBlocked(Exception):
    pass


class RepairWorkflowService:
    ALLOCATION_REQUIRED_STAGE = ClaimStageCode.WORK_ALLOCATION
    REPAIR_STAGE = ClaimStageCode.REPAIR_IN_PROGRESS

    @classmethod
    def ensure_allocation_allowed(cls, job):
        claim = job.claim if job and job.claim_id else None
        if not claim:
            return
        if int(claim.claim_stage or 0) < cls.ALLOCATION_REQUIRED_STAGE:
            raise RepairWorkflowBlocked(
                "Insurance Approval must be completed and the Claim moved "
                "to Work Allocation Pending before allocating repair work."
            )

    @classmethod
    def ensure_start_allowed(cls, job):
        cls.ensure_allocation_allowed(job)

    @classmethod
    def mark_repair_started(cls, job):
        claim = job.claim if job and job.claim_id else None
        if not claim:
            return
        if int(claim.claim_stage or 0) < cls.REPAIR_STAGE:
            claim.claim_stage = cls.REPAIR_STAGE
            claim.status = "Open"
            claim.save(update_fields=["claim_stage", "status"])

    @classmethod
    def progress_is_effective(cls, progress):
        if not progress or not progress.start_time:
            return False
        job = progress.allocation.job if progress.allocation_id else None
        claim = job.claim if job and job.claim_id else None
        return bool(
            not claim
            or int(claim.claim_stage or 0) >= cls.REPAIR_STAGE
        )
