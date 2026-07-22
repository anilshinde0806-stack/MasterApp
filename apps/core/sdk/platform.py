"""
MasterApp Operating System (MOS)
SDK - Platform

Stable exports for platform services.
"""

from __future__ import annotations

from apps.core.platform.authorization import Authorization
from apps.core.platform.cache import Cache
from apps.core.platform.configuration import Configuration
from apps.core.platform.container import Container
from apps.core.platform.feature_flags import FeatureFlags
from apps.core.platform.health import Health, HealthCheck, HealthResult
from apps.core.platform.logger import Logger
from apps.core.platform.module_loader import ModuleLoader
from apps.core.platform.scheduler import ScheduledJob, Scheduler

__all__ = [
    "Authorization",
    "Cache",
    "Configuration",
    "Container",
    "FeatureFlags",
    "Health",
    "HealthCheck",
    "HealthResult",
    "Logger",
    "ModuleLoader",
    "ScheduledJob",
    "Scheduler",
]

