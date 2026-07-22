"""
MasterApp Operating System (MOS)
Runtime - Registry

Central registry for all runtime components.

The Registry is responsible for discovering and storing
modules, business objects, services, workflows and events.

Business modules never communicate directly.
They communicate through the Registry.
"""

from __future__ import annotations

from typing import Any


class Registry:
    """
    Global runtime registry.
    """

    _modules: dict[str, Any] = {}
    _business_objects: dict[str, type] = {}
    _services: dict[str, type] = {}
    _workflows: dict[str, type] = {}
    _events: dict[str, type] = {}

    # ----------------------------------------------------------
    # Modules
    # ----------------------------------------------------------

    @classmethod
    def register_module(cls, module: Any) -> None:
        cls._modules[module.code] = module

    @classmethod
    def get_module(cls, code: str) -> Any | None:
        return cls._modules.get(code)

    @classmethod
    def modules(cls) -> dict[str, Any]:
        return cls._modules.copy()

    # ----------------------------------------------------------
    # Business Objects
    # ----------------------------------------------------------

    @classmethod
    def register_business_object(cls, obj: type) -> None:
        cls._business_objects[obj.__name__] = obj

    @classmethod
    def get_business_object(cls, name: str) -> type | None:
        return cls._business_objects.get(name)

    # ----------------------------------------------------------
    # Services
    # ----------------------------------------------------------

    @classmethod
    def register_service(cls, service: type) -> None:
        cls._services[service.__name__] = service

    @classmethod
    def get_service(cls, name: str) -> type | None:
        return cls._services.get(name)

    # ----------------------------------------------------------
    # Workflows
    # ----------------------------------------------------------

    @classmethod
    def register_workflow(cls, workflow: type) -> None:
        cls._workflows[workflow.__name__] = workflow

    @classmethod
    def get_workflow(cls, name: str) -> type | None:
        return cls._workflows.get(name)

    # ----------------------------------------------------------
    # Events
    # ----------------------------------------------------------

    @classmethod
    def register_event(cls, event: type) -> None:
        cls._events[event.__name__] = event

    @classmethod
    def get_event(cls, name: str) -> type | None:
        return cls._events.get(name)

    # ----------------------------------------------------------
    # Utilities
    # ----------------------------------------------------------

    @classmethod
    def clear(cls) -> None:
        """
        Clears all registered components.

        Mainly used during testing.
        """
        cls._modules.clear()
        cls._business_objects.clear()
        cls._services.clear()
        cls._workflows.clear()
        cls._events.clear()

    @classmethod
    def summary(cls) -> dict[str, int]:
        """
        Returns registry statistics.
        """
        return {
            "modules": len(cls._modules),
            "business_objects": len(cls._business_objects),
            "services": len(cls._services),
            "workflows": len(cls._workflows),
            "events": len(cls._events),
        }