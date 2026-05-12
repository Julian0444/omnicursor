"""CLI bridge: python -m omnicursor.drainer.omnidash_bridge

Drains outbox.jsonl and materializes each event as OmniDash projection fixtures
under <fixtures_dir>/onex.snapshot.projection.live-events.v1/.

Default cursor: ~/.omnicursor/omnidash.cursor (separate from outbox.cursor so
multiple publisher backends can coexist and consume the outbox independently).
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
from pathlib import Path

from omnicursor.drainer.loop import drain_loop, drain_once
from omnicursor.drainer.omnidash_publisher import OmniDashFixturePublisher


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Drain outbox.jsonl and write events as OmniDash projection fixtures."
        )
    )
    parser.add_argument(
        "--outbox",
        type=Path,
        default=Path.home() / ".omnicursor" / "outbox.jsonl",
        metavar="PATH",
        help="Path to outbox.jsonl (default: ~/.omnicursor/outbox.jsonl)",
    )
    parser.add_argument(
        "--cursor",
        type=Path,
        default=Path.home() / ".omnicursor" / "omnidash.cursor",
        metavar="PATH",
        help="Path to cursor file (default: ~/.omnicursor/omnidash.cursor)",
    )
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=Path("/tmp/omnicursor-omnidash-fixtures"),
        metavar="DIR",
        help="Root fixtures dir for OmniDash output (default: /tmp/omnicursor-omnidash-fixtures)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=float(os.environ.get("OMNICURSOR_BRIDGE_INTERVAL", "2")),
        metavar="SECS",
        help="Seconds between drain passes in loop mode (default: 2)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Drain once and exit instead of looping",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    publisher = OmniDashFixturePublisher(fixtures_dir=args.fixtures)

    def _stop(signum, _frame):  # noqa: ANN001
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _stop)

    try:
        if args.once:
            stats = drain_once(
                publisher, outbox_path=args.outbox, cursor_path=args.cursor
            )
            logging.info("drainer stats: %s", stats)
            return 0

        drain_loop(
            publisher,
            interval_s=args.interval,
            outbox_path=args.outbox,
            cursor_path=args.cursor,
        )
        return 0
    except KeyboardInterrupt:
        logging.info("omnidash_bridge: interrupted — exiting cleanly")
        return 0


if __name__ == "__main__":
    sys.exit(main())
