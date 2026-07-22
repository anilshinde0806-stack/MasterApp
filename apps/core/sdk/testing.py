"""
MasterApp Operating System (MOS)
SDK - Testing

Helpers for resetting in-memory MOS state between tests.
"""

from __future__ import annotations

from apps.core.platform.cache import Cache
from apps.core.platform.configuration import Configuration
from apps.core.platform.container import Container
from apps.core.platform.feature_flags import FeatureFlags
from apps.core.platform.health import Health
from apps.core.platform.scheduler import Scheduler
from apps.core.runtime.event_bus import EventBus
from apps.core.runtime.registry import Registry


def reset_mos_state() -> None:
    """
    Clear all in-memory MOS registries.
    """
    Cache.clear()
    Configuration.clear()
    Container.clear()
    EventBus.clear()
    FeatureFlags.clear()
    Health.clear()
    Registry.clear()
    Scheduler.clear()


__all__ = [
    "reset_mos_state",
]

