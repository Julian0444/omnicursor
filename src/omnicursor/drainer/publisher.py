"""Publisher protocol and NoopPublisher (stdlib only).

Publisher is a typing.Protocol so any object with a publish() method is
accepted without inheriting from a base class.  NoopPublisher logs each
event at INFO level and records it in self.events for test inspection.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Protocol, Tuple


class Publisher(Protocol):
    def publish(self, event_type: str, payload: Dict) -> bool:
        """Publish one event.  Returns True on success, False on failure."""
        ...


class NoopPublisher:
    """Publisher that records events in memory and always returns True."""

    def __init__(self, *, log: logging.Logger | None = None) -> None:
        self._log = log or logging.getLogger(__name__)
        self.events: List[Tuple[str, Dict]] = []

    def publish(self, event_type: str, payload: Dict) -> bool:
        self._log.info("drainer.noop.publish %s", event_type)
        self.events.append((event_type, payload))
        return True
