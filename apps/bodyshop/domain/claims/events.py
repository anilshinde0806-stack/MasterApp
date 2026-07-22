"""Claim domain events."""

from dataclasses import dataclass

from apps.core.foundation.domain_event import DomainEvent


@dataclass(slots=True)
class ClaimCreated(DomainEvent):
    claim_id: str = ""
    claim_no: str = ""
    vehicle_id: int = 0
    branch_id: int = 0
    advisor_id: int | None = None

