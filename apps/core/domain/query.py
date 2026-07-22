"""
MasterApp Operating System (MOS)
Domain - Query

Defines the base class for read requests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class Query:
    """
    Base class for all read queries.

    Queries represent requests for information.
    """

    query_id: UUID = field(default_factory=uuid4)

    created_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )

    correlation_id: UUID | None = None

    request_id: UUID | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def query_name(self) -> str:
        """
        Returns the query class name.
        """
        return self.__class__.__name__

    def get(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """
        Retrieve metadata.
        """
        return self.metadata.get(key, default)