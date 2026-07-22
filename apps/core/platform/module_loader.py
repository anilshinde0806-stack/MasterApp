"""
MasterApp Operating System (MOS)
Platform - Module Loader

Discovers, initializes and registers MOS modules.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil

from apps.core.runtime.module import Module
from apps.core.runtime.registry import Registry

logger = logging.getLogger(__name__)


class ModuleLoader:
    """
    Discovers and loads MOS modules.
    """

    @classmethod
    def load(
        cls,
        package: str = "apps",
    ) -> None:
        """
        Discover and initialize all modules.
        """
        root = importlib.import_module(package)

        for module_info in pkgutil.iter_modules(root.__path__):

            module_name = module_info.name

            try:

                mos_module = importlib.import_module(
                    f"{package}.{module_name}.module"
                )

            except ModuleNotFoundError:
                continue

            cls._register_module(mos_module)

    @classmethod
    def _register_module(
        cls,
        imported_module,
    ) -> None:
        """
        Locate Module subclasses and register them.
        """

        for obj in vars(imported_module).values():

            if (
                isinstance(obj, type)
                and issubclass(obj, Module)
                and obj is not Module
            ):

                instance = obj()

                instance.initialize()

                Registry.register_module(instance)

                logger.info(
                    "Loaded module: %s",
                    instance.code,
                )