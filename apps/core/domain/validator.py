"""
MasterApp Operating System (MOS)
Domain - Validator

Defines the base contract for domain validators.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from apps.core.foundation.result import Result

T = TypeVar("T")


class Validator(ABC, Generic[T]):
    """
    Base class for domain validators.
    """

    @abstractmethod
    def validate(self, target: T) -> Result[None]:
        """
        Validate the target object.

        Returns:
            Result.success when validation passes.

            Result.failed when validation fails.
        """

    def __call__(self, target: T) -> Result[None]:
        """
        Allow validator(target) syntax.
        """
        return self.validate(target)