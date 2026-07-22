"""
MasterApp Operating System (MOS)
Core - Foundation
"""

from .aggregate_root import AggregateRoot
from .base_entity import BaseEntity
from .business_object import BusinessObject
from .domain_event import DomainEvent
from .exceptions import (
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
from .result import Result
from .value_object import ValueObject

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
