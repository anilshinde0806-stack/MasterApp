from unittest import TestCase

from apps.bodyshop.application.commands.create_claim import (
    CreateClaimCommand,
    CreateClaimHandler,
    CreateClaimValidator,
)
from apps.bodyshop.domain.claims.claim import Claim, ClaimType
from apps.bodyshop.domain.claims.events import ClaimCreated
from apps.bodyshop.domain.claims.repository import ClaimRepository
from apps.core.domain.unit_of_work import UnitOfWork
from apps.core.foundation.exceptions import ValidationException


class FakeClaimRepository(ClaimRepository):
    def __init__(self) -> None:
        self.claims: list[Claim] = []

    def get(self, claim_id):
        return next((claim for claim in self.claims if claim.id == str(claim_id)), None)

    def add(self, claim: Claim) -> None:
        claim.id = "101"
        for event in claim.domain_events():
            event.claim_id = claim.id
        self.claims.append(claim)

    def claim_no_exists(self, claim_no: str) -> bool:
        return any(claim.claim_no.lower() == claim_no.lower() for claim in self.claims)

    def open_claim_exists_for_vehicle(self, vehicle_id: int) -> bool:
        return any(claim.vehicle_id == vehicle_id for claim in self.claims)

    def open_jobcard_exists_for_vehicle(self, vehicle_id: int) -> bool:
        return False


class FailingClaimRepository(FakeClaimRepository):
    def add(self, claim: Claim) -> None:
        raise RuntimeError("database unavailable")


class FakeUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


class RecordingEventBus:
    events = []

    @classmethod
    def publish(cls, event) -> None:
        cls.events.append(event)


class CreateClaimTests(TestCase):
    def setUp(self) -> None:
        RecordingEventBus.events = []
        self.repository = FakeClaimRepository()
        self.unit_of_work = FakeUnitOfWork()

    def command(self, **overrides) -> CreateClaimCommand:
        values = {"claim_no": "CLM-001", "vehicle_id": 10, "branch_id": 2}
        values.update(overrides)
        return CreateClaimCommand(**values)

    def test_aggregate_creation_is_framework_independent(self):
        claim = Claim.create(claim_no=" CLM-001 ", vehicle_id=10, branch_id=2)
        self.assertEqual(claim.claim_no, "CLM-001")
        self.assertEqual(claim.claim_type, ClaimType.CASHLESS)
        self.assertIsInstance(claim.domain_events()[0], ClaimCreated)

    def test_validator_rejects_duplicate_open_vehicle_claim(self):
        self.repository.add(Claim.create(claim_no="OLD", vehicle_id=10, branch_id=2))
        result = CreateClaimValidator(self.repository).validate(self.command())
        self.assertTrue(result.failed)
        self.assertIn("An open claim already exists for this vehicle.", result.errors)

    def test_handler_persists_commits_then_publishes_event(self):
        handler = CreateClaimHandler(self.repository, self.unit_of_work, RecordingEventBus)
        claim = handler.handle(self.command())
        self.assertEqual(claim.id, "101")
        self.assertTrue(self.unit_of_work.committed)
        self.assertEqual(len(self.repository.claims), 1)
        self.assertEqual(RecordingEventBus.events[0].claim_id, "101")
        self.assertEqual(claim.domain_events(), ())

    def test_handler_does_not_write_invalid_claim(self):
        handler = CreateClaimHandler(self.repository, self.unit_of_work, RecordingEventBus)
        with self.assertRaises(ValidationException):
            handler.handle(self.command(claim_no=""))
        self.assertEqual(self.repository.claims, [])
        self.assertFalse(self.unit_of_work.committed)

    def test_handler_rolls_back_and_does_not_publish_when_write_fails(self):
        repository = FailingClaimRepository()
        handler = CreateClaimHandler(repository, self.unit_of_work, RecordingEventBus)
        with self.assertRaises(RuntimeError):
            handler.handle(self.command())
        self.assertTrue(self.unit_of_work.rolled_back)
        self.assertEqual(RecordingEventBus.events, [])
