"""Claim aggregate with no framework or persistence dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from apps.bodyshop.domain.claims.events import ClaimCreated
from apps.core.foundation.aggregate_root import AggregateRoot


class ClaimType(StrEnum):
    CASHLESS = "Cashless"
    NON_CASHLESS = "NonCashless"
    PAID = "Paid"
    WARRANTY = "Warranty"
    FOC = "FOC"


class ClaimStatus(StrEnum):
    OPEN = "Open"
    CLOSED = "Closed"
    CANCELLED = "Cancelled"


@dataclass(slots=True, kw_only=True)
class Claim(AggregateRoot):
    """Consistency boundary for the Claim lifecycle."""

    claim_no: str
    vehicle_id: int
    branch_id: int
    advisor_id: int | None = None
    insurance_company_id: int | None = None
    claim_type: ClaimType = ClaimType.CASHLESS
    accident_date: date | None = None
    stage: int = 1
    status: ClaimStatus = ClaimStatus.OPEN

    @classmethod
    def create(
        cls,
        *,
        claim_no: str,
        vehicle_id: int,
        branch_id: int,
        advisor_id: int | None = None,
        insurance_company_id: int | None = None,
        claim_type: ClaimType = ClaimType.CASHLESS,
        accident_date: date | None = None,
        created_by: str | None = None,
    ) -> "Claim":
        claim = cls(
            claim_no=claim_no.strip(),
            vehicle_id=vehicle_id,
            branch_id=branch_id,
            advisor_id=advisor_id,
            insurance_company_id=insurance_company_id,
            claim_type=claim_type,
            accident_date=accident_date,
            created_by=created_by,
        )
        claim.add_domain_event(
            ClaimCreated(
                claim_id=claim.id,
                claim_no=claim.claim_no,
                vehicle_id=claim.vehicle_id,
                branch_id=claim.branch_id,
                advisor_id=claim.advisor_id,
            )
        )
        return claim

