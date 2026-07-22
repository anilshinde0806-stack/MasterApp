"""Shared Claim deletion rules, independent of HTTP presentation."""

from django.db import transaction

from apps.claims.repositories.claim_queries import ClaimQueryService
from core.models import Employee, JobCard


class ClaimDeleteError(Exception):
    pass


class ClaimNotFound(ClaimDeleteError):
    pass


class ClaimDeleteForbidden(ClaimDeleteError):
    pass


class ClaimHasJobCard(ClaimDeleteError):
    pass


class ClaimDeleteService:
    @staticmethod
    def _can_delete(user):
        employee = Employee.objects.filter(user=user).first()
        role = (employee.employee_type or "").upper() if employee else ""
        return bool(
            user.is_superuser
            or role in {"ADMIN", "MANAGER"}
            or user.groups.filter(name__iexact="Manager").exists()
        )

    @classmethod
    @transaction.atomic
    def delete(cls, *, claim_id, user):
        claim = ClaimQueryService.visible_to(user).select_for_update().filter(pk=claim_id).first()
        if not claim:
            raise ClaimNotFound("Claim not found.")
        if not cls._can_delete(user):
            raise ClaimDeleteForbidden("Only Admin or Manager can delete a claim.")
        if JobCard.objects.filter(claim=claim).exists():
            raise ClaimHasJobCard(
                "Claim cannot be deleted because a Job Card exists."
            )

        claim_no = claim.claim_no
        claim.delete()
        return claim_no
