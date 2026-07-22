"""
MasterApp Operating System (MOS)
Platform - Scheduler

Framework-independent scheduler.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Callable
from uuid import UUID, uuid4


@dataclass(slots=True)
class ScheduledJob:
    """
    Represents a scheduled job.
    """

    name: str

    action: Callable[[], None]

    interval: timedelta

    job_id: UUID = field(default_factory=uuid4)

    last_run: datetime | None = None

    enabled: bool = True

    def should_run(self) -> bool:

        if not self.enabled:
            return False

        if self.last_run is None:
            return True

        return (
            datetime.now(UTC)
            >= self.last_run + self.interval
        )

    def execute(self) -> None:

        self.action()

        self.last_run = datetime.now(UTC)


class Scheduler:
    """
    Platform scheduler.
    """

    _jobs: dict[str, ScheduledJob] = {}

    @classmethod
    def register(
        cls,
        job: ScheduledJob,
    ) -> None:

        cls._jobs[job.name] = job

    @classmethod
    def unregister(
        cls,
        name: str,
    ) -> None:

        cls._jobs.pop(name, None)

    @classmethod
    def get(
        cls,
        name: str,
    ) -> ScheduledJob | None:

        return cls._jobs.get(name)

    @classmethod
    def run_pending(cls) -> None:

        for job in cls._jobs.values():

            if job.should_run():

                job.execute()

    @classmethod
    def clear(cls) -> None:

        cls._jobs.clear()

    @classmethod
    def jobs(
        cls,
    ) -> list[ScheduledJob]:

        return list(cls._jobs.values())