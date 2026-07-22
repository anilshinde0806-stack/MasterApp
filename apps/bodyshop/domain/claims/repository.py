"""Persistence-independent Claim repository contract."""

from __future__ import annotations

from abc import ABC, abstractmethod

from apps.bodyshop.domain.claims.claim import Claim


class ClaimRepository(ABC):
    @abstractmethod
    def get(self, claim_id: str | int) -> Claim | None:
        pass

    @abstractmethod
    def add(self, claim: Claim) -> None:
        pass

    @abstractmethod
    def claim_no_exists(self, claim_no: str) -> bool:
        pass

    @abstractmethod
    def open_claim_exists_for_vehicle(self, vehicle_id: int) -> bool:
        pass

    @abstractmethod
    def open_jobcard_exists_for_vehicle(self, vehicle_id: int) -> bool:
        pass
