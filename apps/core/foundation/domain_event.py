"""
MasterApp Operating System (MOS)
Foundation - Domain Event

Base class for all domain events.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class DomainEvent:
    """
    Base class for all domain events.

    Domain events represent business facts that have already happened.
    """

    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    correlation_id: str | None = None
    request_id: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def event_name(self) -> str:
        """
        Returns the event class name.
        """
        return self.__class__.__name__

    def set(self, key: str, value: Any) -> None:
        """
        Store event metadata.
        """
        self.metadata[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve event metadata.
        """
        return self.metadata.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the event to a dictionary.
        """
        return asdict(self)