"""
MasterApp Operating System (MOS)
Platform - Authorization

Central authorization service.
"""

from __future__ import annotations

from apps.core.platform.feature_flags import FeatureFlags


class Authorization:
    """
    Platform authorization service.
    """

    @classmethod
    def authorize(
        cls,
        permission: str,
        context,
    ) -> bool:
        """
        Returns True if access is granted.
        """

        # ----------------------------------------
        # Authentication
        # ----------------------------------------

        if not context.is_authenticated:
            return False

        # ----------------------------------------
        # Feature Flag
        # ----------------------------------------

        if FeatureFlags.is_disabled(permission):
            return False

        # ----------------------------------------
        # Permissions
        # ----------------------------------------

        permissions = context.get(
            "permissions",
            set(),
        )

        return permission in permissions

    @classmethod
    def require(
        cls,
        permission: str,
        context,
    ) -> None:
        """
        Raise an exception if permission is denied.
        """

        if not cls.authorize(
            permission,
            context,
        ):
            raise PermissionError(
                f"Permission denied: {permission}"
            )