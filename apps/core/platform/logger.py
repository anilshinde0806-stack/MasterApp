"""
MasterApp Operating System (MOS)
Platform - Logger

Provides structured logging with application context.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("mos")


class Logger:
    """
    Platform logging service.
    """

    @staticmethod
    def debug(
        message: str,
        context=None,
        **properties: Any,
    ) -> None:
        logger.debug(
            Logger._format(
                message,
                context,
                properties,
            )
        )

    @staticmethod
    def info(
        message: str,
        context=None,
        **properties: Any,
    ) -> None:
        logger.info(
            Logger._format(
                message,
                context,
                properties,
            )
        )

    @staticmethod
    def warning(
        message: str,
        context=None,
        **properties: Any,
    ) -> None:
        logger.warning(
            Logger._format(
                message,
                context,
                properties,
            )
        )

    @staticmethod
    def error(
        message: str,
        context=None,
        **properties: Any,
    ) -> None:
        logger.error(
            Logger._format(
                message,
                context,
                properties,
            )
        )

    @staticmethod
    def exception(
        message: str,
        context=None,
        **properties: Any,
    ) -> None:
        logger.exception(
            Logger._format(
                message,
                context,
                properties,
            )
        )

    @staticmethod
    def _format(
        message: str,
        context,
        properties: dict[str, Any],
    ) -> str:

        payload = {
            "message": message,
            **properties,
        }

        if context is not None:

            payload.update(
                {
                    "request_id": context.request_id,
                    "correlation_id": context.correlation_id,
                    "user_id": context.user_id,
                    "company_id": context.company_id,
                    "branch_id": context.branch_id,
                }
            )

        return str(payload)