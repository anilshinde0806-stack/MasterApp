"""
MasterApp Operating System (MOS)
Infrastructure - Logger Provider

Python logging adapter.
"""

from __future__ import annotations

import logging


class LoggerProvider:
    """
    Provides configured Python loggers.
    """

    @staticmethod
    def get(name: str = "mos") -> logging.Logger:
        return logging.getLogger(name)
