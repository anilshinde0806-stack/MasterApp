"""
MasterApp Operating System (MOS)
Foundation - Exceptions

Defines the exception hierarchy used throughout MOS.
"""

from __future__ import annotations


class MOSException(Exception):
    """
    Base exception for the MasterApp Operating System.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str = "MOS_ERROR",
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


# ----------------------------------------------------------------------
# Business Exceptions
# ----------------------------------------------------------------------


class BusinessException(MOSException):
    """Business rule violation."""


class ValidationException(MOSException):
    """Validation failure."""


class PermissionException(MOSException):
    """Permission denied."""


class WorkflowException(MOSException):
    """Workflow error."""


class RepositoryException(MOSException):
    """Repository operation failed."""


class NotFoundException(MOSException):
    """Requested resource not found."""


class ConfigurationException(MOSException):
    """Invalid configuration."""


class IntegrationException(MOSException):
    """External system error."""


class AuthenticationException(MOSException):
    """Authentication failed."""


class AuthorizationException(MOSException):
    """Authorization failed."""