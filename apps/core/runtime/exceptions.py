"""
Runtime exceptions for the MasterApp Operating System (MOS).
"""

from __future__ import annotations


class RuntimeException(Exception):
    """Base exception for the runtime layer."""


class ModuleAlreadyRegistered(RuntimeException):
    """Raised when a module is registered more than once."""


class ModuleNotFound(RuntimeException):
    """Raised when a requested module is not registered."""


class ServiceAlreadyRegistered(RuntimeException):
    """Raised when a service already exists."""


class BusinessObjectAlreadyRegistered(RuntimeException):
    """Raised when a business object already exists."""


class WorkflowAlreadyRegistered(RuntimeException):
    """Raised when a workflow already exists."""


class EventAlreadyRegistered(RuntimeException):
    """Raised when an event already exists."""