"""
MasterApp Operating System (MOS)
Core - Domain
"""

from .command import Command
from .query import Query
from .repository import Repository
from .service import Service
from .specification import (
    AndSpecification,
    NotSpecification,
    OrSpecification,
    Specification,
)
from .unit_of_work import UnitOfWork
from .validator import Validator

__all__ = [
    "AndSpecification",
    "Command",
    "NotSpecification",
    "OrSpecification",
    "Query",
    "Repository",
    "Service",
    "Specification",
    "UnitOfWork",
    "Validator",
]
