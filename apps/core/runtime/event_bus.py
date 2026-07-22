"""
MasterApp Operating System (MOS)
Runtime - Event Bus

Provides synchronous publish/subscribe messaging between
runtime components.

Business modules should communicate through events
instead of direct service calls.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


EventHandler = Callable[[Any], None]


class EventBus:
    """
    In-process synchronous Event Bus.
    """

    _subscribers: dict[type, list[EventHandler]] = defaultdict(list)

    # ---------------------------------------------------------
    # Subscription
    # ---------------------------------------------------------

    @classmethod
    def subscribe(
        cls,
        event_type: type,
        handler: EventHandler,
    ) -> None:
        """
        Register an event handler.
        """
        if handler not in cls._subscribers[event_type]:
            cls._subscribers[event_type].append(handler)

    # ---------------------------------------------------------

    @classmethod
    def unsubscribe(
        cls,
        event_type: type,
        handler: EventHandler,
    ) -> None:
        """
        Remove an event handler.
        """
        handlers = cls._subscribers.get(event_type)

        if handlers and handler in handlers:
            handlers.remove(handler)

    # ---------------------------------------------------------
    # Publish
    # ---------------------------------------------------------

    @classmethod
    def publish(cls, event: Any) -> None:
        """
        Publish an event to all registered subscribers.
        """
        event_type = type(event)

        handlers = cls._subscribers.get(event_type, [])

        logger.debug(
            "Publishing %s to %d subscriber(s).",
            event_type.__name__,
            len(handlers),
        )

        for handler in handlers:
            try:
                handler(event)

            except Exception:
                logger.exception(
                    "Event handler failed for %s",
                    event_type.__name__,
                )

    # ---------------------------------------------------------

    @classmethod
    def subscriber_count(
        cls,
        event_type: type,
    ) -> int:
        return len(cls._subscribers.get(event_type, []))

    # ---------------------------------------------------------

    @classmethod
    def clear(cls) -> None:
        """
        Clear all subscribers.

        Mainly used during testing.
        """
        cls._subscribers.clear()