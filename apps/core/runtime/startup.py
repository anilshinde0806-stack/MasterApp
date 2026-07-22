"""
MOS Runtime Startup
"""

from __future__ import annotations

import logging
from time import perf_counter

from apps.core.platform.module_loader import ModuleLoader
from apps.core.platform.health import Health

logger = logging.getLogger(__name__)


class Startup:
    """
    Bootstraps the MOS runtime.
    """

    @classmethod
    def initialize(cls) -> None:
        start = perf_counter()

        logger.info("=" * 60)
        logger.info("Starting MasterApp Operating System")
        logger.info("=" * 60)

        logger.info("Loading platform configuration...")

        logger.info("Initializing dependency container...")

        logger.info("Loading business modules...")
        ModuleLoader.load()

        logger.info("Running health checks...")
        report = Health.run()

        logger.info(
            "Health Status: %s",
            "Healthy" if report["healthy"] else "Unhealthy",
        )

        elapsed = (perf_counter() - start) * 1000

        logger.info("=" * 60)
        logger.info(
            "MasterApp Operating System Ready (%.2f ms)",
            elapsed,
        )
        logger.info("=" * 60)