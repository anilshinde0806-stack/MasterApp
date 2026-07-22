"""
MasterApp Operating System (MOS)
Foundation - Business Object

Defines the metadata and behavior contract for business objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class BusinessObject:
    """
    Base class describing a business object.

    A BusinessObject provides metadata used by the platform
    to build UI, workflows, permissions, APIs and reports.
    """

    code: str

    name: str

    description: str = ""

    module: str = ""

    icon: str = ""

    aggregate_type: type | None = None

    repository_type: type | None = None

    service_type: type | None = None

    workflow_type: type | None = None

    permissions: list[str] = field(default_factory=list)

    search_fields: list[str] = field(default_factory=list)

    display_fields: list[str] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def qualified_name(self) -> str:
        """
        Returns the fully qualified business object name.
        """
        if self.module:
            return f"{self.module}.{self.code}"

        return self.code

    def add_permission(self, permission: str) -> None:
        """
        Register a permission.
        """
        if permission not in self.permissions:
            self.permissions.append(permission)

    def add_search_field(self, field_name: str) -> None:
        """
        Register a searchable field.
        """
        if field_name not in self.search_fields:
            self.search_fields.append(field_name)

    def add_display_field(self, field_name: str) -> None:
        """
        Register a display field.
        """
        if field_name not in self.display_fields:
            self.display_fields.append(field_name)

    def set(self, key: str, value: Any) -> None:
        """
        Store metadata.
        """
        self.metadata[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve metadata.
        """
        return self.metadata.get(key, default)