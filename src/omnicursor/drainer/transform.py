"""Pure outbox-row → events transform (no I/O, no logging).

Mapping is bit-compatible with the live send_event calls in
.cursor/hooks/scripts/stop.py (C0.3), so a downstream consumer cannot
distinguish the live path from the durable replay path.
"""

from __future__ import annotations

from typing import Dict, List, Tuple


def outbox_row_to_events(row: Dict) -> List[Tuple[str, Dict]]:
    """Map one outbox row to a list of (event_type, payload) tuples.

    Returns [] for non-session-outcome rows (e.g. hook events, socket events).
    Always returns at least one tuple for "session.outcome" on session outcome rows.
    Appends a second tuple for "utilization.scoring.requested" only when
    ``injected_pattern_ids`` is a non-empty list. If the key is missing
    (legacy rows), it is treated like an empty list — only ``session.outcome``
    is emitted.

    Raises KeyError if any required field is missing — callers must catch
    this and treat the row as a poison line (advance cursor, log warning).
    """
    if row.get("schema_version") != "omnicursor.session_outcome.v1":
        return []

    outcome: str = row["session_outcome"]
    reason: str = row["session_outcome_reason"]
    session_id: str = row["conversation_id"]
    correlation_id: str = row["correlation_id"]

    error = (
        {
            "code": "session_failed",
            "message": reason,
            "component": "omnicursor",
        }
        if outcome == "failed"
        else None
    )

    payload1: Dict = {
        "session_id": session_id,
        "outcome": outcome,
        "reason": reason,
        "correlation_id": correlation_id,
        "matched_agent": row.get("matched_agent"),
        "matched_confidence": row.get("matched_confidence"),
        "files_edited": row.get("files_edited", 0),
        "started_at": row.get("started_at"),
        "ended_at": row.get("ended_at"),
        "error": error,
    }

    events: List[Tuple[str, Dict]] = [("session.outcome", payload1)]

    injected = row.get("injected_pattern_ids")
    if injected:
        payload2: Dict = {
            "session_id": session_id,
            "correlation_id": correlation_id,
            "session_outcome": outcome,
            "injected_pattern_ids": injected,
        }
        events.append(("utilization.scoring.requested", payload2))

    return events
