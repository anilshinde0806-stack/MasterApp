"""Create Claim command pipeline."""

from dataclasses import dataclass
from datetime import date

from apps.bodyshop.domain.claims.claim import Claim, ClaimType
from apps.bodyshop.domain.claims.repository import ClaimRepository
from apps.core.domain.command import Command
from apps.core.domain.unit_of_work import UnitOfWork
from apps.core.foundation.exceptions import ValidationException
from apps.core.foundation.result import Result
from apps.core.runtime.event_bus import EventBus


@dataclass(slots=True, kw_only=True)
class CreateClaimCommand(Command):
    claim_no: str
    vehicle_id: int
    branch_id: int
    advisor_id: int | None = None
    insurance_company_id: int | None = None
    claim_type: str = ClaimType.CASHLESS.value
    accident_date: date | None = None
    requested_by: str | None = None


class CreateClaimValidator:
    def __init__(self, repository: ClaimRepository) -> None:
        self.repository = repository

    def validate(self, command: CreateClaimCommand) -> Result[None]:
        errors: list[str] = []
        claim_no = command.claim_no.strip()
        if not claim_no:
            errors.append("Claim number is required.")
        elif self.repository.claim_no_exists(claim_no):
            errors.append("Claim number already exists.")
        if command.vehicle_id <= 0:
            errors.append("Vehicle is required.")
        elif self.repository.open_claim_exists_for_vehicle(command.vehicle_id):
            errors.append("An open claim already exists for this vehicle.")
        elif self.repository.open_jobcard_exists_for_vehicle(command.vehicle_id):
            errors.append("An open jobcard already exists for this vehicle.")
        if command.branch_id <= 0:
            errors.append("Branch is required.")
        try:
            ClaimType(command.claim_type)
        except ValueError:
            errors.append("Claim type is invalid.")
        if errors:
            return Result.fail("Claim validation failed.", errors)
        return Result.ok()


class CreateClaimHandler:
    def __init__(
        self,
        repository: ClaimRepository,
        unit_of_work: UnitOfWork,
        event_bus: type[EventBus] = EventBus,
    ) -> None:
        self.repository = repository
        self.unit_of_work = unit_of_work
        self.event_bus = event_bus
        self.validator = CreateClaimValidator(repository)

    def handle(self, command: CreateClaimCommand) -> Claim:
        validation = self.validator.validate(command)
        if validation.failed:
            raise ValidationException(
                "; ".join(validation.errors), code="CLAIM_VALIDATION_FAILED"
            )
        claim = Claim.create(
            claim_no=command.claim_no,
            vehicle_id=command.vehicle_id,
            branch_id=command.branch_id,
            advisor_id=command.advisor_id,
            insurance_company_id=command.insurance_company_id,
            claim_type=ClaimType(command.claim_type),
            accident_date=command.accident_date,
            created_by=command.requested_by,
        )
        events = claim.collect_domain_events()
        with self.unit_of_work:
            self.repository.add(claim)
        for event in events:
            self.event_bus.publish(event)
        claim.clear_all_domain_events()
        return claim
