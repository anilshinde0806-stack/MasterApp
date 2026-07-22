"""
MasterApp Operating System (MOS)
Infrastructure - Scheduler Provider

Adapter around the platform scheduler.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

from apps.core.platform.scheduler import ScheduledJob, Scheduler


class SchedulerProvider:
    """
    Registers and runs scheduled jobs through the platform scheduler.
    """

    @staticmethod
    def register(
        name: str,
        action: Callable[[], None],
        interval: timedelta,
    ) -> ScheduledJob:
        job = ScheduledJob(
            name=name,
            action=action,
            interval=interval,
        )

        Scheduler.register(job)

        return job

    @staticmethod
    def unregister(name: str) -> None:
        Scheduler.unregister(name)

    @staticmethod
    def run_pending() -> None:
        Scheduler.run_pending()

    @staticmethod
    def jobs() -> list[ScheduledJob]:
        return Scheduler.jobs()
