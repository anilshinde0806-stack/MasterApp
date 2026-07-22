"""Django ORM adapter for the Claim aggregate."""

from apps.bodyshop.domain.claims.claim import Claim, ClaimStatus, ClaimType
from apps.bodyshop.domain.claims.repository import ClaimRepository
from core.models import Claim as ClaimModel
from core.models import ClaimStageCode
from core.models import JobCard
from django.db.models import Q


class DjangoClaimRepository(ClaimRepository):
    def get(self, claim_id: str | int) -> Claim | None:
        model = ClaimModel.objects.filter(pk=claim_id).first()
        return self._to_domain(model) if model else None

    def add(self, claim: Claim) -> None:
        model = ClaimModel.objects.create(
            claim_no=claim.claim_no,
            vehicle_id=claim.vehicle_id,
            branch_id=claim.branch_id,
            employee_id=claim.advisor_id,
            insurance_company_id=claim.insurance_company_id,
            claim_type=claim.claim_type.value,
            accident_date=claim.accident_date,
            claim_stage=claim.stage,
            status=claim.status.value,
        )
        claim.id = str(model.pk)
        claim.created_at = model.created_at
        claim.updated_at = model.updated_at
        for event in claim.domain_events():
            if hasattr(event, "claim_id"):
                event.claim_id = claim.id

    def claim_no_exists(self, claim_no: str) -> bool:
        return ClaimModel.objects.filter(claim_no__iexact=claim_no.strip()).exists()

    def open_claim_exists_for_vehicle(self, vehicle_id: int) -> bool:
        return (
            ClaimModel.objects.filter(vehicle_id=vehicle_id)
            .exclude(claim_stage=ClaimStageCode.CLOSED)
            .exclude(
                status__in=(
                    ClaimStatus.CLOSED.value,
                    ClaimStatus.CANCELLED.value,
                )
            )
            .exists()
        )

    def open_jobcard_exists_for_vehicle(self, vehicle_id: int) -> bool:
        return (
            JobCard.objects.filter(
                Q(claim__vehicle_id=vehicle_id) | Q(vehicle_id=vehicle_id)
            )
            .exclude(repair_status__iexact="Closed")
            .exists()
        )

    @staticmethod
    def _to_domain(model: ClaimModel) -> Claim:
        return Claim(
            id=str(model.pk),
            claim_no=model.claim_no,
            vehicle_id=model.vehicle_id,
            branch_id=model.branch_id,
            advisor_id=model.employee_id,
            insurance_company_id=model.insurance_company_id,
            claim_type=ClaimType(model.claim_type),
            accident_date=model.accident_date,
            stage=model.claim_stage,
            status=ClaimStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
