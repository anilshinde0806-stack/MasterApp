"""
MasterApp Operating System (MOS)
Infrastructure - ORM

Small Django ORM helpers shared by persistence adapters.
"""

from __future__ import annotations

from typing import Any

from django.db.models import Model, QuerySet


class ORM:
    """
    Utility methods for working with Django models.
    """

    @staticmethod
    def to_dict(
        instance: Model,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        field_names = fields or [
            field.name
            for field in instance._meta.fields
        ]

        return {
            field_name: getattr(instance, field_name)
            for field_name in field_names
        }

    @staticmethod
    def one(queryset: QuerySet) -> Model:
        return queryset.get()

    @staticmethod
    def exists(queryset: QuerySet) -> bool:
        return queryset.exists()
