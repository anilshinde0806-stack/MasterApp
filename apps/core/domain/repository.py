"""
MasterApp Operating System (MOS)
Domain - Repository

Defines the repository contract for aggregate roots.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID

from apps.core.foundation.aggregate_root import AggregateRoot

T = TypeVar("T", bound=AggregateRoot)


class Repository(ABC, Generic[T]):
    """
    Contract for aggregate repositories.

    Concrete implementations belong to the Infrastructure layer.
    """

    @abstractmethod
    def get(self, entity_id: UUID) -> T | None:
        """
        Return an aggregate by its identifier.
        """

    @abstractmethod
    def add(self, entity: T) -> None:
        """
        Persist a new aggregate.
        """

    @abstractmethod
    def update(self, entity: T) -> None:
        """
        Persist changes to an aggregate.
        """

    @abstractmethod
    def delete(self, entity: T) -> None:
        """
        Remove an aggregate.
        """

    @abstractmethod
    def exists(self, entity_id: UUID) -> bool:
        """
        Check whether an aggregate exists.
        """

    @abstractmethod
    def list(self) -> list[T]:
        """
        Return all aggregates.
        """

    @abstractmethod
    def count(self) -> int:
        """
        Return aggregate count.
        """