"""
MasterApp Operating System (MOS)
Domain - Unit of Work

Defines the transaction boundary for business operations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class UnitOfWork(ABC):
    """
    Coordinates repositories and transactions.

    Concrete implementations belong to the Infrastructure layer.
    """

    @abstractmethod
    def commit(self) -> None:
        """
        Commit the current transaction.
        """

    @abstractmethod
    def rollback(self) -> None:
        """
        Roll back the current transaction.
        """

    def __enter__(self) -> "UnitOfWork":
        """
        Enter the transaction scope.
        """
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> bool:
        """
        Complete the transaction.

        Commit if no exception occurred,
        otherwise rollback.
        """
        if exc_type is None:
            self.commit()
        else:
            self.rollback()

        return False