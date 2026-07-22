"""
MasterApp Operating System (MOS)
Infrastructure - Health Provider

Django infrastructure health checks.
"""

from __future__ import annotations

from apps.core.infrastructure.persistence.database import Database
from apps.core.platform.health import Health, HealthCheck, HealthResult


class DatabaseHealthCheck(HealthCheck):
    """
    Health check for the configured Django database.
    """

    @property
    def name(self) -> str:
        return "database"

    def check(self) -> HealthResult:
        healthy = Database.available()

        return HealthResult(
            name=self.name,
            healthy=healthy,
            message="available" if healthy else "unavailable",
        )


class HealthProvider:
    """
    Registers infrastructure health checks.
    """

    @staticmethod
    def register_defaults() -> None:
        Health.register(DatabaseHealthCheck())

    @staticmethod
    def run():
        return Health.run()
