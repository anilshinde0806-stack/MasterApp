"""
MasterApp Operating System (MOS)
Foundation - Aggregate Root

Defines the base class for all aggregate roots.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .base_entity import BaseEntity


@dataclass(slots=True)
class AggregateRoot(BaseEntity):
    """
    Base class for aggregate roots.

    Aggregate roots act as the consistency boundary for a group
    of related entities.
    """

    _children: list[BaseEntity] = field(
        default_factory=list,
        init=False,
        repr=False,
    )

    # ---------------------------------------------------------
    # Child Management
    # ---------------------------------------------------------

    def add_child(self, entity: BaseEntity) -> None:
        """
        Add a child entity to the aggregate.
        """
        self._children.append(entity)

    def remove_child(self, entity: BaseEntity) -> None:
        """
        Remove a child entity from the aggregate.
        """
        if entity in self._children:
            self._children.remove(entity)

    def children(self) -> tuple[BaseEntity, ...]:
        """
        Return all child entities.
        """
        return tuple(self._children)

    # ---------------------------------------------------------
    # Domain Events
    # ---------------------------------------------------------

    def collect_domain_events(self):
        """
        Return all pending events from the aggregate and its children.
        """
        events = list(self.domain_events())

        for child in self._children:
            events.extend(child.domain_events())

        return tuple(events)

    def clear_all_domain_events(self) -> None:
        """
        Clear pending events from the aggregate and all children.
        """
        self.clear_domain_events()

        for child in self._children:
            child.clear_domain_events()