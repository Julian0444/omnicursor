"""KafkaPublisher — produces drained events to Redpanda/Kafka.

Requires ``confluent-kafka`` (not in the stdlib; isolated to the sidecar
process so hooks stay dependency-free).

Event routing follows config/event_registry/omnicursor.yaml:
  session.outcome            → onex.cmd.omniintelligence.session-outcome.v1
                             → onex.evt.omnicursor.session-outcome.v1
  utilization.scoring.requested → onex.cmd.omniintelligence.utilization-scoring.v1
  prompt.submitted           → onex.evt.omnicursor.prompt-submitted.v1

Graceful degradation: if confluent-kafka is not installed, publish() always
returns False and logs a clear error. The drainer loop handles this as a
permanent failure and stops.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Dict, List

_log = logging.getLogger(__name__)

# Event type → list of Kafka topics to fan out to.
# Mirrors config/event_registry/omnicursor.yaml.
_TOPIC_MAP: Dict[str, List[str]] = {
    "session.outcome": [
        "onex.cmd.omniintelligence.session-outcome.v1",
        "onex.evt.omnicursor.session-outcome.v1",
    ],
    "utilization.scoring.requested": [
        "onex.cmd.omniintelligence.utilization-scoring.v1",
    ],
    "prompt.submitted": [
        "onex.evt.omnicursor.prompt-submitted.v1",
    ],
}

_DEFAULT_BOOTSTRAP = "localhost:29092"


def _bootstrap_servers() -> str:
    return os.environ.get("KAFKA_BOOTSTRAP_SERVERS") or _DEFAULT_BOOTSTRAP


class KafkaPublisher:
    """Publisher that produces events to Kafka/Redpanda.

    Instantiation is lazy — the Producer is created on first publish() call
    so import errors (missing confluent-kafka) surface only when actually used.
    """

    def __init__(
        self,
        bootstrap_servers: str | None = None,
        *,
        log: logging.Logger | None = None,
    ) -> None:
        self._bootstrap = bootstrap_servers or _bootstrap_servers()
        self._log = log or _log
        self._producer = None
        self._available: bool | None = None  # None = not yet probed

    def _get_producer(self):
        if self._producer is not None:
            return self._producer
        try:
            from confluent_kafka import Producer  # type: ignore[import]
        except ImportError:
            self._log.error(
                "confluent-kafka is not installed. "
                "Install it in the sidecar venv: pip install confluent-kafka"
            )
            self._available = False
            return None
        self._producer = Producer({"bootstrap.servers": self._bootstrap})
        self._available = True
        return self._producer

    def publish(self, event_type: str, payload: Dict) -> bool:
        """Produce *payload* to all topics mapped from *event_type*.

        Returns True only if every topic received the message. False on any
        producer or serialization error.
        """
        producer = self._get_producer()
        if producer is None:
            return False

        topics = _TOPIC_MAP.get(event_type)
        if not topics:
            self._log.warning("KafkaPublisher: unknown event_type %r — dropping", event_type)
            return False

        try:
            value = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
        except (TypeError, ValueError) as exc:
            self._log.error("KafkaPublisher: serialization error: %s", exc)
            return False

        partition_key_field = _partition_key_field(event_type)
        key = payload.get(partition_key_field, "")
        key_bytes = str(key).encode() if key else None

        success = True
        for topic in topics:
            try:
                producer.produce(topic, value=value, key=key_bytes)
            except Exception as exc:
                self._log.error("KafkaPublisher: produce to %r failed: %s", topic, exc)
                success = False

        if success:
            try:
                producer.poll(0)  # trigger delivery callbacks without blocking
            except Exception:
                pass

        return success

    def flush(self, timeout_s: float = 5.0) -> None:
        """Flush pending messages. Call before process exit."""
        if self._producer is not None:
            try:
                self._producer.flush(timeout=timeout_s)
            except Exception as exc:
                self._log.warning("KafkaPublisher: flush error: %s", exc)


def _partition_key_field(event_type: str) -> str:
    return "session_id"


def topics_for(event_type: str) -> List[str]:
    """Return the Kafka topics an event_type fans out to."""
    return list(_TOPIC_MAP.get(event_type, []))
