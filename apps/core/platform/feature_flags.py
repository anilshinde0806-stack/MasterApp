"""
MasterApp Operating System (MOS)
Platform - Feature Flags

Centralized feature toggle management.
"""

from __future__ import annotations


class FeatureFlags:
    """
    Central feature flag registry.
    """

    _flags: dict[str, bool] = {}

    # ---------------------------------------------------------
    # Registration
    # ---------------------------------------------------------

    @classmethod
    def enable(
        cls,
        name: str,
    ) -> None:
        """
        Enable a feature.
        """
        cls._flags[name] = True

    @classmethod
    def disable(
        cls,
        name: str,
    ) -> None:
        """
        Disable a feature.
        """
        cls._flags[name] = False

    # ---------------------------------------------------------
    # Query
    # ---------------------------------------------------------

    @classmethod
    def is_enabled(
        cls,
        name: str,
    ) -> bool:
        """
        Return True if feature is enabled.
        """
        return cls._flags.get(name, False)

    @classmethod
    def is_disabled(
        cls,
        name: str,
    ) -> bool:
        """
        Return True if feature is disabled.
        """
        return not cls.is_enabled(name)

    # ---------------------------------------------------------
    # Utilities
    # ---------------------------------------------------------

    @classmethod
    def remove(
        cls,
        name: str,
    ) -> None:
        """
        Remove a feature flag.
        """
        cls._flags.pop(name, None)

    @classmethod
    def clear(cls) -> None:
        """
        Remove all feature flags.
        """
        cls._flags.clear()

    @classmethod
    def all(cls) -> dict[str, bool]:
        """
        Return all registered feature flags.
        """
        return dict(cls._flags)