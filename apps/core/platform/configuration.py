"""
MasterApp Operating System (MOS)
Platform - Configuration

Provides centralized configuration management.
"""

from __future__ import annotations

from typing import Any


class Configuration:
    """
    Central configuration registry.
    """

    _values: dict[str, Any] = {}

    # ---------------------------------------------------------
    # Registration
    # ---------------------------------------------------------

    @classmethod
    def set(
        cls,
        key: str,
        value: Any,
    ) -> None:
        """
        Store a configuration value.
        """
        cls._values[key] = value

    # ---------------------------------------------------------

    @classmethod
    def get(
        cls,
        key: str,
        default: Any = None,
    ) -> Any:
        """
        Retrieve a configuration value.
        """
        return cls._values.get(key, default)

    # ---------------------------------------------------------

    @classmethod
    def has(
        cls,
        key: str,
    ) -> bool:
        """
        Check whether a configuration key exists.
        """
        return key in cls._values

    # ---------------------------------------------------------

    @classmethod
    def remove(
        cls,
        key: str,
    ) -> None:
        """
        Remove a configuration value.
        """
        cls._values.pop(key, None)

    # ---------------------------------------------------------

    @classmethod
    def clear(cls) -> None:
        """
        Remove all configuration values.
        """
        cls._values.clear()

    # ---------------------------------------------------------

    @classmethod
    def all(cls) -> dict[str, Any]:
        """
        Return a copy of all configuration values.
        """
        return dict(cls._values)