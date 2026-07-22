"""
MasterApp Operating System (MOS)
Foundation - Base Entity

Defines the base class for all domain entities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from .domain_event import DomainEvent


@dataclass(slots=True)
class BaseEntity:
    """
    Base class for all domain entities.

    Entities have identity and lifecycle.
    """

    id: str = field(default_factory=lambda: str(uuid4()))

    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    updated_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    created_by: str | None = None
    updated_by: str | None = None

    _domain_events: list[DomainEvent] = field(
        default_factory=list,
        init=False,
        repr=False,
    )

    # ---------------------------------------------------------
    # Domain Events
    # ---------------------------------------------------------

    def add_domain_event(self, event: DomainEvent) -> None:
        """
        Register a domain event.
        """
        self._domain_events.append(event)

    def domain_events(self) -> tuple[DomainEvent, ...]:
        """
        Return all pending domain events.
        """
        return tuple(self._domain_events)

    def clear_domain_events(self) -> None:
        """
        Remove all pending domain events.
        """
        self._domain_events.clear()

    # ---------------------------------------------------------
    # Audit
    # ---------------------------------------------------------

    def touch(self, user_id: str | None = None) -> None:
        """
        Update audit information.
        """
        self.updated_at = datetime.now(UTC)
        self.updated_by = user_id

    # ---------------------------------------------------------
    # Equality
    # ---------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BaseEntity):
            return NotImplemented

        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)