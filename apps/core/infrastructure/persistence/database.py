"""
MasterApp Operating System (MOS)
Infrastructure - Database

Database connection utilities for Django.
"""

from __future__ import annotations

from typing import Any

from django.db import connections
from django.db.utils import OperationalError


class Database:
    """
    Thin wrapper around Django database connections.
    """

    @staticmethod
    def connection(alias: str = "default") -> Any:
        return connections[alias]

    @staticmethod
    def available(alias: str = "default") -> bool:
        try:
            with connections[alias].cursor():
                return True
        except OperationalError:
            return False

    @staticmethod
    def close(alias: str = "default") -> None:
        connections[alias].close()
