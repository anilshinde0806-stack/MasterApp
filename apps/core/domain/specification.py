"""
MasterApp Operating System (MOS)
Domain - Specification

Defines reusable business rule specifications.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class Specification(ABC, Generic[T]):
    """
    Base class for business specifications.
    """

    @abstractmethod
    def is_satisfied_by(self, candidate: T) -> bool:
        """
        Return True when the candidate satisfies
        this specification.
        """

    def __call__(self, candidate: T) -> bool:
        """
        Allow specification(candidate) syntax.
        """
        return self.is_satisfied_by(candidate)

    def __and__(self, other: "Specification[T]") -> "Specification[T]":
        return AndSpecification(self, other)

    def __or__(self, other: "Specification[T]") -> "Specification[T]":
        return OrSpecification(self, other)

    def __invert__(self) -> "Specification[T]":
        return NotSpecification(self)
class AndSpecification(Specification[T]):

    def __init__(
        self,
        left: Specification[T],
        right: Specification[T],
    ):
        self.left = left
        self.right = right

    def is_satisfied_by(self, candidate: T) -> bool:
        return (
            self.left.is_satisfied_by(candidate)
            and
            self.right.is_satisfied_by(candidate)
        )


class OrSpecification(Specification[T]):

    def __init__(
        self,
        left: Specification[T],
        right: Specification[T],
    ):
        self.left = left
        self.right = right

    def is_satisfied_by(self, candidate: T) -> bool:
        return (
            self.left.is_satisfied_by(candidate)
            or
            self.right.is_satisfied_by(candidate)
        )


class NotSpecification(Specification[T]):

    def __init__(
        self,
        specification: Specification[T],
    ):
        self.specification = specification

    def is_satisfied_by(self, candidate: T) -> bool:
        return not self.specification.is_satisfied_by(candidate)
