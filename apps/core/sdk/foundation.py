"""
MasterApp Operating System (MOS)
SDK - Foundation

Stable exports for base entities, value objects, results and exceptions.
"""

from __future__ import annotations

from apps.core.foundation.aggregate_root import AggregateRoot
from apps.core.foundation.base_entity import BaseEntity
from apps.core.foundation.business_object import BusinessObject
from apps.core.foundation.domain_event import DomainEvent
from apps.core.foundation.exceptions import (
    AuthenticationException,
    AuthorizationException,
    BusinessException,
    ConfigurationException,
    IntegrationException,
    MOSException,
    NotFoundException,
    PermissionException,
    RepositoryException,
    ValidationException,
    WorkflowException,
)
from apps.core.foundation.result import Result
from apps.core.foundation.value_object import ValueObject

__all__ = [
    "AggregateRoot",
    "AuthenticationException",
    "AuthorizationException",
    "BaseEntity",
    "BusinessException",
    "BusinessObject",
    "ConfigurationException",
    "DomainEvent",
    "IntegrationException",
    "MOSException",
    "NotFoundException",
    "PermissionException",
    "RepositoryException",
    "Result",
    "ValidationException",
    "ValueObject",
    "WorkflowException",
]

