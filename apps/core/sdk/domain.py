"""
MasterApp Operating System (MOS)
SDK - Domain

Stable exports for domain contracts.
"""

from __future__ import annotations

from apps.core.domain.command import Command
from apps.core.domain.query import Query
from apps.core.domain.repository import Repository
from apps.core.domain.service import Service
from apps.core.domain.specification import Specification
from apps.core.domain.unit_of_work import UnitOfWork
from apps.core.domain.validator import Validator

__all__ = [
    "Command",
    "Query",
    "Repository",
    "Service",
    "Specification",
    "UnitOfWork",
    "Validator",
]

