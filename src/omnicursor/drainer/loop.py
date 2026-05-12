"""Drain loop — converts outbox rows to events and hands them to a Publisher (stdlib only).

drain_once reads from the current cursor offset, publishes all events for
each row, and advances the cursor only after every event for that row is
successfully published.

Poison-line policy:
- Invalid JSON → log warning, advance cursor (do not block forever).
- KeyError on required fields → log warning, advance cursor.
- Publisher returns False → stop immediately, leave cursor un-advanced.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Dict, Optional

from omnicursor.drainer.cursor import read_offset, write_offset
from omnicursor.drainer.publisher import Publisher
from omnicursor.drainer.reader import read_complete_lines
from omnicursor.drainer.transform import outbox_row_to_events

_log = logging.getLogger(__name__)


def drain_once(
    publisher: Publisher,
    *,
    outbox_path: Optional[Path] = None,
    cursor_path: Optional[Path] = None,
    logger: Optional[logging.Logger] = None,
) -> Dict:
    """Read new outbox rows from the cursor offset and publish their events.

    Returns a stats dict:
      rows_processed   — rows whose events were all published successfully
      events_published — total publish() calls that returned True
      rows_skipped     — poison rows (bad JSON / missing keys); cursor advanced
      rows_failed_publish — rows stopped mid-publish; cursor NOT advanced
      final_offset     — byte offset at the end of this drain
    """
    log = logger or _log
    offset = read_offset(cursor_path)

    rows_processed = 0
    events_published = 0
    rows_skipped = 0
    rows_failed_publish = 0

    for line_text, next_offset in read_complete_lines(offset, outbox_path):
        # Parse JSON.
        try:
            row = json.loads(line_text)
        except (json.JSONDecodeError, ValueError):
            log.warning("drainer: invalid JSON at offset %d — skipping", offset)
            write_offset(next_offset, cursor_path)
            offset = next_offset
            rows_skipped += 1
            continue

        # Build events.
        try:
            events = outbox_row_to_events(row)
        except KeyError as exc:
            log.warning(
                "drainer: missing required field %s at offset %d — skipping",
                exc,
                offset,
            )
            write_offset(next_offset, cursor_path)
            offset = next_offset
            rows_skipped += 1
            continue

        # Publish all events for this row.
        all_ok = True
        for event_type, payload in events:
            try:
                ok = publisher.publish(event_type, payload)
            except Exception as exc:
                log.warning(
                    "drainer: publisher raised for %s at offset %d — stopping: %s",
                    event_type,
                    offset,
                    exc,
                )
                all_ok = False
                break
            if ok:
                events_published += 1
            else:
                log.warning(
                    "drainer: publisher returned False for %s at offset %d — stopping",
                    event_type,
                    offset,
                )
                all_ok = False
                break

        if not all_ok:
            rows_failed_publish += 1
            break

        write_offset(next_offset, cursor_path)
        offset = next_offset
        rows_processed += 1

    return {
        "rows_processed": rows_processed,
        "events_published": events_published,
        "rows_skipped": rows_skipped,
        "rows_failed_publish": rows_failed_publish,
        "final_offset": offset,
    }


def drain_loop(
    publisher: Publisher,
    *,
    interval_s: float = 5.0,
    outbox_path: Optional[Path] = None,
    cursor_path: Optional[Path] = None,
    logger: Optional[logging.Logger] = None,
    max_iterations: Optional[int] = None,
    stop_event: Optional[threading.Event] = None,
) -> None:
    """Run drain_once in a loop, sleeping interval_s between iterations.

    max_iterations limits the loop count (useful for tests).  None = forever.
    stop_event, when set, terminates the loop after the current iteration.
    Exits cleanly on KeyboardInterrupt.  Any other exception is logged and
    the loop continues (the drainer must not crash on a single bad iteration).
    """
    log = logger or _log
    iteration = 0
    while max_iterations is None or iteration < max_iterations:
        if stop_event is not None and stop_event.is_set():
            break
        try:
            drain_once(
                publisher,
                outbox_path=outbox_path,
                cursor_path=cursor_path,
                logger=log,
            )
        except KeyboardInterrupt:
            log.info("drainer: received KeyboardInterrupt — exiting loop")
            return
        except Exception as exc:
            log.exception("drainer: unexpected error in drain_once: %s", exc)
        iteration += 1
        if max_iterations is None or iteration < max_iterations:
            if stop_event is not None:
                stop_event.wait(timeout=interval_s)
            else:
                time.sleep(interval_s)
