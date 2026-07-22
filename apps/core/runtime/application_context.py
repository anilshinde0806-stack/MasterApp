"""
MasterApp Operating System (MOS)
Runtime - Application Context

The ApplicationContext carries execution information that is shared
throughout the lifetime of a request, background job, or scheduled task.

Business services should receive an ApplicationContext instead of
passing user, company, branch, etc. individually.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class ApplicationContext:
    """
    Execution context for the current application request.

    This object is immutable except for the metadata dictionary,
    which allows modules to attach additional runtime information.
    """

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    user_id: int | None = None
    company_id: int | None = None
    branch_id: int | None = None

    # ------------------------------------------------------------------
    # Localization
    # ------------------------------------------------------------------

    language: str = "en"
    timezone: str = "Asia/Kolkata"

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------

    database_alias: str = "default"

    # ------------------------------------------------------------------
    # Request Tracking
    # ------------------------------------------------------------------

    request_id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: str = field(default_factory=lambda: str(uuid4()))

    # ------------------------------------------------------------------
    # Runtime Metadata
    # ------------------------------------------------------------------

    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Metadata API
    # ------------------------------------------------------------------

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

    def has(self, key: str) -> bool:
        """
        Check whether metadata exists.
        """
        return key in self.metadata

    def remove(self, key: str) -> None:
        """
        Remove metadata if present.
        """
        self.metadata.pop(key, None)

    def clear(self) -> None:
        """
        Clear all runtime metadata.
        """
        self.metadata.clear()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def is_authenticated(self) -> bool:
        """
        Returns True when a user is associated with this context.
        """
        return self.user_id is not None

    def __str__(self) -> str:
        return (
            f"ApplicationContext("
            f"user={self.user_id}, "
            f"company={self.company_id}, "
            f"branch={self.branch_id}, "
            f"request={self.request_id})"
        )