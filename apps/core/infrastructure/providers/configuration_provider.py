"""
MasterApp Operating System (MOS)
Infrastructure - Configuration Provider

Django settings adapter for platform configuration.
"""

from __future__ import annotations

import os
from typing import Any

from django.conf import settings


class ConfigurationProvider:
    """
    Reads configuration from Django settings with environment fallback.
    """

    @staticmethod
    def get(
        key: str,
        default: Any = None,
    ) -> Any:
        return getattr(settings, key, os.getenv(key, default))

    @staticmethod
    def has(key: str) -> bool:
        return hasattr(settings, key) or key in os.environ

    @staticmethod
    def require(key: str) -> Any:
        value = ConfigurationProvider.get(key)

        if value is None:
            raise KeyError(f"Missing required configuration: {key}")

        return value
