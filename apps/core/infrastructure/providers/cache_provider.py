"""
MasterApp Operating System (MOS)
Infrastructure - Cache Provider

Django cache adapter for the platform cache boundary.
"""

from __future__ import annotations

from typing import Any

from django.core.cache import cache


class CacheProvider:
    """
    Cache provider backed by Django's configured cache backend.
    """

    @staticmethod
    def set(
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        cache.set(key, value, timeout=ttl)

    @staticmethod
    def get(
        key: str,
        default: Any = None,
    ) -> Any:
        return cache.get(key, default)

    @staticmethod
    def exists(key: str) -> bool:
        return cache.get(key) is not None

    @staticmethod
    def remove(key: str) -> None:
        cache.delete(key)

    @staticmethod
    def clear() -> None:
        cache.clear()
