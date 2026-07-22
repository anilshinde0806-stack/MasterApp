"""
MasterApp Operating System (MOS)
Infrastructure - Django Unit of Work

Transaction boundary implementation using Django transactions.
"""

from __future__ import annotations

from types import TracebackType

from django.db import transaction

from apps.core.domain.unit_of_work import UnitOfWork


class DjangoUnitOfWork(UnitOfWork):
    """
    Unit of work backed by ``transaction.atomic``.
    """

    def __init__(
        self,
        using: str | None = None,
        savepoint: bool = True,
    ) -> None:
        self.using = using
        self.savepoint = savepoint
        self._atomic = None

    def __enter__(self) -> "DjangoUnitOfWork":
        self._atomic = transaction.atomic(
            using=self.using,
            savepoint=self.savepoint,
        )
        self._atomic.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        if self._atomic is None:
            return False

        return self._atomic.__exit__(
            exc_type,
            exc_value,
            traceback,
        )

    def commit(self) -> None:
        """
        Commit is handled by ``transaction.atomic`` on context exit.
        """

    def rollback(self) -> None:
        """
        Mark the active transaction for rollback.
        """
        transaction.set_rollback(True, using=self.using)
