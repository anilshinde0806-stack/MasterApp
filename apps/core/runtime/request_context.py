"""
MasterApp Operating System (MOS)
Runtime - Request Context

Represents transport-specific information for an incoming request.

This object is intentionally separated from ApplicationContext
so business services remain independent of HTTP.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RequestContext:
    """
    Request-specific execution context.
    """

    method: str = ""
    path: str = ""
    client_ip: str = ""
    user_agent: str = ""

    host: str = ""
    scheme: str = "http"

    headers: dict[str, str] = field(default_factory=dict)
    query_params: dict[str, Any] = field(default_factory=dict)

    metadata: dict[str, Any] = field(default_factory=dict)

    # ---------------------------------------------------------

    def header(self, name: str, default: str | None = None) -> str | None:
        """
        Return a request header.
        """
        return self.headers.get(name, default)

    # ---------------------------------------------------------

    def set(self, key: str, value: Any) -> None:
        self.metadata[key] = value

    # ---------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        return self.metadata.get(key, default)

    # ---------------------------------------------------------

    def has(self, key: str) -> bool:
        return key in self.metadata

    # ---------------------------------------------------------

    def remove(self, key: str) -> None:
        self.metadata.pop(key, None)

    # ---------------------------------------------------------

    def clear(self) -> None:
        self.metadata.clear()