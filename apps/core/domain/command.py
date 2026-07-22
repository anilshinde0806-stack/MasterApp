"""
MasterApp Operating System (MOS)
Domain - Command

Defines the base class for business commands.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4


@dataclass(slots=True)
class Command:
    """
    Base class for all business commands.

    A command represents the intent to perform
    a business operation.
    """

    command_id: UUID = field(default_factory=uuid4)

    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    correlation_id: UUID | None = None

    request_id: UUID | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def command_name(self) -> str:
        """
        Returns the command class name.
        """
        return self.__class__.__name__

    def set(self, key: str, value: Any) -> None:
        """
        Store command metadata.
        """
        self.metadata[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve command metadata.
        """
        return self.metadata.get(key, default)