"""
MasterApp Operating System (MOS)
Foundation - Value Object

Base class for immutable value objects.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ValueObject:
    """
    Base class for all value objects.

    Value objects:
    - are immutable
    - have no identity
    - are compared by value
    """

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the value object into a dictionary.
        """
        return asdict(self)

    def __repr__(self) -> str:
        values = ", ".join(
            f"{k}={v!r}"
            for k, v in self.to_dict().items()
        )
        return f"{self.__class__.__name__}({values})"