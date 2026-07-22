"""
MasterApp Operating System (MOS)
Platform - Health Monitoring

Framework-independent health monitoring.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------
# Health Result
# ---------------------------------------------------------

@dataclass(slots=True)
class HealthResult:

    name: str

    healthy: bool

    message: str = ""

    details: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------
# Health Check
# ---------------------------------------------------------

class HealthCheck(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def check(self) -> HealthResult:
        ...


# ---------------------------------------------------------
# Health Registry
# ---------------------------------------------------------

class Health:

    _checks: list[HealthCheck] = []

    @classmethod
    def register(
        cls,
        check: HealthCheck,
    ) -> None:

        cls._checks.append(check)

    @classmethod
    def clear(cls) -> None:

        cls._checks.clear()

    @classmethod
    def run(cls) -> dict[str, Any]:

        results: list[HealthResult] = []

        healthy = True

        started = datetime.now(UTC)

        for check in cls._checks:

            try:

                result = check.check()

            except Exception as ex:

                result = HealthResult(

                    name=check.name,

                    healthy=False,

                    message=str(ex),

                )

            healthy &= result.healthy

            results.append(result)

        return {

            "healthy": healthy,

            "timestamp": started,

            "checks": results,

        }