"""
MasterApp Operating System (MOS)
Domain - Service

Defines the base contract for domain services.
"""

from __future__ import annotations

from abc import ABC
from typing import Any

from apps.core.foundation.result import Result


class Service(ABC):
    """
    Base class for all domain services.

    Domain services coordinate business operations using
    repositories, validators and unit of work implementations.
    """

    def ok(
        self,
        value: Any = None,
        message: str = "",
    ) -> Result[Any]:
        """
        Return a successful result.
        """
        return Result.ok(
            value=value,
            message=message,
        )

    def fail(
        self,
        message: str,
        *,
        errors: list[str] | None = None,
    ) -> Result[Any]:
        """
        Return a failed result.
        """
        return Result.fail(
            message=message,
            errors=errors or [],
        )

    def validate(
        self,
        condition: bool,
        message: str,
    ) -> Result[None]:
        """
        Validate a business rule.

        Returns a failed Result when the condition is False.
        """
        if condition:
            return self.ok()

        return self.fail(message)