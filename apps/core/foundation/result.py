"""
MasterApp Operating System (MOS)
Foundation - Result

Represents the outcome of an operation.

Instead of returning None, tuples, or raising exceptions for expected
business outcomes, services should return a Result object.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class Result(Generic[T]):
    """
    Represents the outcome of an operation.
    """

    success: bool
    message: str = ""
    data: T | None = None
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def failed(self) -> bool:
        """
        Returns True when the operation failed.
        """
        return not self.success

    def add_error(self, error: str) -> None:
        """
        Add an error message.
        """
        self.errors.append(error)

    def set(self, key: str, value: Any) -> None:
        """
        Store runtime metadata.
        """
        self.metadata[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve runtime metadata.
        """
        return self.metadata.get(key, default)

    @classmethod
    def ok(
        cls,
        data: T | None = None,
        message: str = "",
    ) -> "Result[T]":
        """
        Create a successful result.
        """
        return cls(
            success=True,
            message=message,
            data=data,
        )

    @classmethod
    def fail(
        cls,
        message: str,
        errors: list[str] | None = None,
    ) -> "Result[T]":
        """
        Create a failed result.
        """
        return cls(
            success=False,
            message=message,
            errors=errors or [],
        )