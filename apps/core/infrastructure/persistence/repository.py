"""
MasterApp Operating System (MOS)
Infrastructure - Repository

Django-backed repository implementation for aggregate persistence.
"""

from __future__ import annotations

from typing import Generic, TypeVar
from uuid import UUID

from django.db.models import Model

from apps.core.domain.repository import Repository
from apps.core.foundation.aggregate_root import AggregateRoot

T = TypeVar("T", bound=AggregateRoot)
M = TypeVar("M", bound=Model)


class DjangoRepository(Repository[T], Generic[T, M]):
    """
    Base repository backed by a Django model.

    Subclasses may override ``to_domain`` and ``to_model`` when domain
    aggregates differ from ORM models.
    """

    model_class: type[M]

    def __init__(self, model_class: type[M] | None = None) -> None:
        if model_class is not None:
            self.model_class = model_class

        if not hasattr(self, "model_class"):
            raise ValueError("model_class must be provided.")

    def get(self, entity_id: UUID) -> T | None:
        model = self.model_class.objects.filter(pk=entity_id).first()

        if model is None:
            return None

        return self.to_domain(model)

    def add(self, entity: T) -> None:
        model = self.to_model(entity)
        model.save(force_insert=True)

    def update(self, entity: T) -> None:
        model = self.to_model(entity)
        model.save()

    def delete(self, entity: T) -> None:
        self.model_class.objects.filter(pk=entity.id).delete()

    def exists(self, entity_id: UUID) -> bool:
        return self.model_class.objects.filter(pk=entity_id).exists()

    def list(self) -> list[T]:
        return [
            self.to_domain(model)
            for model in self.model_class.objects.all()
        ]

    def count(self) -> int:
        return self.model_class.objects.count()

    def to_domain(self, model: M) -> T:
        return model  # type: ignore[return-value]

    def to_model(self, entity: T) -> M:
        return entity  # type: ignore[return-value]
