"""
MasterApp Operating System (MOS)
Platform - Cache

Framework-independent cache abstraction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass(slots=True)
class CacheItem:
    """
    Represents a cached value.
    """

    value: Any

    expires_at: datetime | None = None

    @property
    def expired(self) -> bool:
        if self.expires_at is None:
            return False

        return datetime.now(UTC) >= self.expires_at


class Cache:
    """
    Simple in-memory cache.
    """

    _cache: dict[str, CacheItem] = {}

    # ---------------------------------------------------------
    # Store
    # ---------------------------------------------------------

    @classmethod
    def set(
        cls,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:

        expires = None

        if ttl is not None:
            expires = datetime.now(UTC) + timedelta(
                seconds=ttl
            )

        cls._cache[key] = CacheItem(
            value=value,
            expires_at=expires,
        )

    # ---------------------------------------------------------
    # Retrieve
    # ---------------------------------------------------------

    @classmethod
    def get(
        cls,
        key: str,
        default: Any = None,
    ) -> Any:

        item = cls._cache.get(key)

        if item is None:
            return default

        if item.expired:

            cls.remove(key)

            return default

        return item.value

    # ---------------------------------------------------------

    @classmethod
    def exists(
        cls,
        key: str,
    ) -> bool:

        return cls.get(key) is not None

    # ---------------------------------------------------------

    @classmethod
    def remove(
        cls,
        key: str,
    ) -> None:

        cls._cache.pop(key, None)

    # ---------------------------------------------------------

    @classmethod
    def clear(cls) -> None:

        cls._cache.clear()