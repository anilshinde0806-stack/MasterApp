"""
MasterApp Operating System (MOS)
Runtime - Module

Base class for every business module.

Examples:
    - BodyShopModule
    - InventoryModule
    - CRMModule
    - AccountsModule
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Module:
    """
    Base class for every MOS module.

    Each module describes itself and the components it provides.
    """

    # ------------------------------------------------------------------
    # Basic Information
    # ------------------------------------------------------------------

    name: str
    code: str
    version: str = "1.0.0"
    description: str = ""

    # ------------------------------------------------------------------
    # Registration Collections
    # ------------------------------------------------------------------

    business_objects: list[type] = field(default_factory=list)

    services: list[type] = field(default_factory=list)

    workflows: list[type] = field(default_factory=list)

    events: list[type] = field(default_factory=list)

    permissions: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Lifecycle Hooks
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """
        Called once during MOS startup.
        Override in derived modules if required.
        """
        pass

    def shutdown(self) -> None:
        """
        Called during application shutdown.
        """
        pass

    # ------------------------------------------------------------------
    # Registration Helpers
    # ------------------------------------------------------------------

    def register_business_object(self, obj: type) -> None:
        self.business_objects.append(obj)

    def register_service(self, service: type) -> None:
        self.services.append(service)

    def register_workflow(self, workflow: type) -> None:
        self.workflows.append(workflow)

    def register_event(self, event: type) -> None:
        self.events.append(event)

    def register_permission(self, permission: str) -> None:
        self.permissions.append(permission)

    # ------------------------------------------------------------------
    # Information
    # ------------------------------------------------------------------

    @property
    def object_count(self) -> int:
        return len(self.business_objects)

    @property
    def service_count(self) -> int:
        return len(self.services)

    def __str__(self) -> str:
        return f"{self.code} ({self.version})"