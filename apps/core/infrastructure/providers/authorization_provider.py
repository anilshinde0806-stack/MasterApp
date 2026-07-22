"""
MasterApp Operating System (MOS)
Infrastructure - Authorization Provider

Django user permission adapter.
"""

from __future__ import annotations

from typing import Any


class AuthorizationProvider:
    """
    Checks Django user permissions.
    """

    @staticmethod
    def authorize(
        user: Any,
        permission: str,
        obj: Any = None,
    ) -> bool:
        if user is None:
            return False

        if not getattr(user, "is_authenticated", False):
            return False

        return bool(user.has_perm(permission, obj))

    @staticmethod
    def require(
        user: Any,
        permission: str,
        obj: Any = None,
    ) -> None:
        if not AuthorizationProvider.authorize(
            user,
            permission,
            obj,
        ):
            raise PermissionError(
                f"Permission denied: {permission}"
            )
