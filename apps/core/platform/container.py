"""
MasterApp Operating System (MOS)
Platform - Dependency Injection Container

Provides lightweight dependency registration and resolution.
"""

from __future__ import annotations

from typing import Any


class Container:
    """
    Lightweight dependency injection container.
    """

    _registrations: dict[type, type] = {}
    _singletons: dict[type, Any] = {}

    # ---------------------------------------------------------
    # Registration
    # ---------------------------------------------------------

    @classmethod
    def register(
        cls,
        interface: type,
        implementation: type,
    ) -> None:
        """
        Register an implementation for an interface.
        """
        cls._registrations[interface] = implementation

    @classmethod
    def register_instance(
        cls,
        interface: type,
        instance: Any,
    ) -> None:
        """
        Register a singleton instance.
        """
        cls._singletons[interface] = instance

    # ---------------------------------------------------------
    # Resolution
    # ---------------------------------------------------------

    @classmethod
    def resolve(
        cls,
        interface: type,
    ) -> Any:
        """
        Resolve a dependency.
        """
        if interface in cls._singletons:
            return cls._singletons[interface]

        implementation = cls._registrations.get(interface)

        if implementation is None:
            raise KeyError(
                f"No registration found for "
                f"{interface.__name__}"
            )

        return implementation()

    # ---------------------------------------------------------
    # Utilities
    # ---------------------------------------------------------

    @classmethod
    def contains(
        cls,
        interface: type,
    ) -> bool:
        """
        Check whether an interface is registered.
        """
        return (
            interface in cls._registrations
            or interface in cls._singletons
        )

    @classmethod
    def unregister(
        cls,
        interface: type,
    ) -> None:
        """
        Remove a registration.
        """
        cls._registrations.pop(interface, None)
        cls._singletons.pop(interface, None)

    @classmethod
    def clear(cls) -> None:
        """
        Remove all registrations.
        """
        cls._registrations.clear()
        cls._singletons.clear()