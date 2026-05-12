"""OmniDashFixturePublisher — materializes drained events as OmniDash projection fixtures.

Writes projection JSON files to <fixtures_dir>/onex.snapshot.projection.live-events.v1/
so the OmniDash Express bridge (OMNIDASH_DATA_SOURCE=file) can serve them at
GET /projection/:topic.

All file writes are atomic via tempfile.mkstemp + os.replace.  No Kafka, stdlib only.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

TOPIC = "onex.snapshot.projection.live-events.v1"


def _atomic_write_json(path: Path, data: object) -> None:
    fd, tmp_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(",", ":"), ensure_ascii=False)
        os.replace(tmp_path, path)
    except Exception:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise


def _type_for(event_type: str, payload: Dict) -> str:
    if event_type == "session.outcome":
        outcome = payload.get("outcome")
        if outcome == "success":
            return "ACTION"
        if outcome == "failed":
            return "ERROR"
        return "TRANSFORMATION"
    if event_type == "utilization.scoring.requested":
        return "TRANSFORMATION"
    return "ACTION"


def _summary_for(event_type: str, payload: Dict) -> str:
    if event_type == "session.outcome":
        outcome = payload.get("outcome") or "?"
        agent = payload.get("matched_agent") or "no-agent"
        files = payload.get("files_edited") or 0
        return f"{outcome} · {agent} · {files} file{'s' if files != 1 else ''}"
    if event_type == "utilization.scoring.requested":
        n = len(payload.get("injected_pattern_ids") or [])
        outcome = payload.get("session_outcome") or "?"
        return f"{n} pattern{'s' if n != 1 else ''} scored · {outcome}"
    return event_type


class OmniDashFixturePublisher:
    """Publisher that writes events as OmniDash-compatible projection fixture files.

    The projection topic directory is <fixtures_dir>/<TOPIC>/.
    After each publish():
      - <i>.json holds one LiveEvent row (widget interface shape).
      - index.json holds ["0.json", "1.json", ...] for the current event list.

    Events are kept newest-first; the list is trimmed to max_live_events after
    each append.  Orphan <i>.json files from prior longer lists remain on disk
    but are not referenced by index.json, so readers ignore them.
    """

    def __init__(self, fixtures_dir: Path, max_live_events: int = 200) -> None:
        self._fixtures_dir = fixtures_dir
        self._topic_dir = fixtures_dir / TOPIC
        self._max_live_events = max_live_events
        self._live_events: List[Dict] = []

    def publish(self, event_type: str, payload: Dict) -> bool:
        try:
            event: Dict = {
                "id": f"omnicursor-{uuid.uuid4().hex[:12]}",
                "type": _type_for(event_type, payload),
                "timestamp": datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
                "source": "omnicursor",
                "topic": f"onex.evt.omnicursor.{event_type.replace('.', '-')}.v1",
                "summary": _summary_for(event_type, payload),
                "payload": json.dumps(
                    payload, separators=(",", ":"), ensure_ascii=False
                ),
            }
            self._live_events.append(event)
            self._live_events.sort(key=lambda e: e["timestamp"], reverse=True)
            self._live_events = self._live_events[: self._max_live_events]

            self._topic_dir.mkdir(parents=True, exist_ok=True)
            for i, ev in enumerate(self._live_events):
                _atomic_write_json(self._topic_dir / f"{i}.json", ev)
            index = [f"{i}.json" for i in range(len(self._live_events))]
            _atomic_write_json(self._topic_dir / "index.json", index)
            return True
        except Exception:
            return False
