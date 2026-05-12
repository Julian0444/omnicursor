"""OmniCursor sidecar daemon — CLI entry point.

python -m omnicursor.sidecar.daemon [--publisher kafka|omnidash|noop]

Runs two concurrent loops:
  1. socket_listener  — binds ~/.omnicursor/emit.sock, receives live hook events,
                        appends them to outbox.jsonl (bridges live → durable path)
  2. drain_loop       — polls outbox.jsonl every --interval seconds and publishes
                        new rows via the selected Publisher

Publishers:
  kafka     Produce to Redpanda/Kafka (requires confluent-kafka, KAFKA_BOOTSTRAP_SERVERS)
  omnidash  Write OmniDash projection fixtures (no Kafka; for local demo)
  noop      Log events only; no external output (useful for testing)

Signals:
  SIGTERM / SIGINT → flush publisher, remove socket, exit 0
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
from pathlib import Path
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
_log = logging.getLogger("omnicursor.sidecar")


def _make_publisher(name: str, fixtures_dir: Optional[Path], bootstrap: Optional[str]):
    if name == "kafka":
        from omnicursor.drainer.kafka_publisher import KafkaPublisher
        return KafkaPublisher(bootstrap_servers=bootstrap, log=_log)
    if name == "omnidash":
        from omnicursor.drainer.omnidash_publisher import OmniDashFixturePublisher
        fd = fixtures_dir or Path("/tmp/omnicursor-omnidash-fixtures")
        return OmniDashFixturePublisher(fixtures_dir=fd, log=_log)
    from omnicursor.drainer.publisher import NoopPublisher
    return NoopPublisher(log=_log)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="OmniCursor sidecar: socket listener + outbox drainer"
    )
    parser.add_argument(
        "--publisher",
        choices=["kafka", "omnidash", "noop"],
        default="omnidash",
        help="Event publisher backend (default: omnidash)",
    )
    parser.add_argument(
        "--outbox",
        type=Path,
        default=Path.home() / ".omnicursor" / "outbox.jsonl",
        metavar="PATH",
    )
    parser.add_argument(
        "--socket",
        type=Path,
        default=Path.home() / ".omnicursor" / "emit.sock",
        metavar="PATH",
    )
    parser.add_argument(
        "--cursor",
        type=Path,
        default=Path.home() / ".omnicursor" / "sidecar.cursor",
        metavar="PATH",
        help="Drain cursor file (tracks outbox read offset)",
    )
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=Path("/tmp/omnicursor-omnidash-fixtures"),
        metavar="DIR",
        help="Fixtures dir for omnidash publisher",
    )
    parser.add_argument(
        "--kafka-bootstrap",
        metavar="SERVERS",
        default=None,
        help="Kafka bootstrap servers (overrides KAFKA_BOOTSTRAP_SERVERS env var)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        metavar="SECONDS",
        help="Drain poll interval in seconds (default: 2)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Drain once and exit (no socket listener, no loop)",
    )
    args = parser.parse_args(argv)

    publisher = _make_publisher(args.publisher, args.fixtures, args.kafka_bootstrap)
    _log.info(
        "sidecar starting | publisher=%s outbox=%s socket=%s interval=%.1fs",
        args.publisher,
        args.outbox,
        args.socket,
        args.interval,
    )

    from omnicursor.drainer.loop import drain_loop, drain_once

    if args.once:
        stats = drain_once(
            publisher,
            outbox_path=args.outbox,
            cursor_path=args.cursor,
        )
        _log.info("drain_once stats: %s", stats)
        _flush(publisher)
        return 0

    stop_event = threading.Event()

    def _shutdown(signum, frame):
        _log.info("sidecar received signal %s — shutting down", signum)
        stop_event.set()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    # Start socket listener in background thread.
    from omnicursor.sidecar.socket_listener import start as start_listener
    try:
        start_listener(
            socket_path=args.socket,
            outbox_path=args.outbox,
            stop_event=stop_event,
            logger=_log,
        )
    except OSError as exc:
        _log.error("socket listener failed to start: %s", exc)
        return 1

    # Run drain loop in the main thread (blocks until stop_event).
    drain_loop(
        publisher,
        outbox_path=args.outbox,
        cursor_path=args.cursor,
        interval_s=args.interval,
        stop_event=stop_event,
    )

    _flush(publisher)
    _log.info("sidecar stopped")
    return 0


def _flush(publisher) -> None:
    flush = getattr(publisher, "flush", None)
    if flush is not None:
        try:
            flush()
        except Exception as exc:
            _log.warning("publisher flush error: %s", exc)


if __name__ == "__main__":
    sys.exit(main())
