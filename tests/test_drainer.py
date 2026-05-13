"""Tests for src/omnicursor/drainer/."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

from omnicursor.drainer.cursor import read_offset, write_offset
from omnicursor.drainer.loop import drain_once
from omnicursor.drainer.publisher import NoopPublisher
from omnicursor.drainer.reader import read_complete_lines
from omnicursor.drainer.transform import outbox_row_to_events


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row(**extra) -> Dict:
    base: Dict = {
        "schema_version": "omnicursor.session_outcome.v1",
        "source": "omnicursor",
        "conversation_id": "conv-1",
        "correlation_id": "corr-1",
        "session_outcome": "success",
        "session_outcome_reason": "completion markers found",
        "matched_agent": "debugging",
        "matched_confidence": 0.9,
        "files_edited": 2,
        "languages": ["python"],
        "started_at": "2026-05-11T10:00:00Z",
        "ended_at": "2026-05-11T10:05:00Z",
        "injected_pattern_ids": [],
    }
    base.update(extra)
    return base


def _write_outbox(path: Path, rows: List[Dict]) -> None:
    """Append rows as newline-terminated JSON lines."""
    with path.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, separators=(",", ":")) + "\n")


class _FailingPublisher:
    """Always returns False on publish."""

    def publish(self, event_type: str, payload: Dict) -> bool:
        return False


class _RaisingPublisher:
    """Always raises RuntimeError on publish."""

    def publish(self, event_type: str, payload: Dict) -> bool:
        raise RuntimeError("publish exploded")


class _RecordingPublisher:
    """Returns True and records calls."""

    def __init__(self) -> None:
        self.events: List[Tuple[str, Dict]] = []

    def publish(self, event_type: str, payload: Dict) -> bool:
        self.events.append((event_type, payload))
        return True


# ---------------------------------------------------------------------------
# cursor.py
# ---------------------------------------------------------------------------


class TestCursor:
    def test_read_offset_missing_file_returns_zero(self, tmp_path: Path) -> None:
        assert read_offset(tmp_path / "no.cursor") == 0

    def test_read_offset_valid_integer(self, tmp_path: Path) -> None:
        p = tmp_path / "out.cursor"
        p.write_text("42\n")
        assert read_offset(p) == 42

    def test_write_then_read_roundtrip(self, tmp_path: Path) -> None:
        p = tmp_path / "out.cursor"
        assert write_offset(100, p) is True
        assert read_offset(p) == 100

    def test_corrupt_cursor_non_numeric_falls_back_to_zero(self, tmp_path: Path) -> None:
        p = tmp_path / "out.cursor"
        p.write_text("not a number\n")
        assert read_offset(p) == 0

    def test_corrupt_cursor_negative_falls_back_to_zero(self, tmp_path: Path) -> None:
        p = tmp_path / "out.cursor"
        p.write_text("-5\n")
        assert read_offset(p) == 0

    def test_corrupt_cursor_multiline_garbage_falls_back_to_zero(self, tmp_path: Path) -> None:
        p = tmp_path / "out.cursor"
        p.write_text("abc\n123\n")
        assert read_offset(p) == 0

    def test_write_offset_creates_parent_dir(self, tmp_path: Path) -> None:
        p = tmp_path / "nested" / "dir" / "out.cursor"
        assert write_offset(7, p) is True
        assert read_offset(p) == 7

    def test_write_offset_is_atomic(self, tmp_path: Path) -> None:
        p = tmp_path / "out.cursor"
        write_offset(10, p)
        write_offset(20, p)
        assert read_offset(p) == 20


# ---------------------------------------------------------------------------
# reader.py
# ---------------------------------------------------------------------------


class TestReader:
    def test_empty_file_yields_nothing(self, tmp_path: Path) -> None:
        outbox = tmp_path / "outbox.jsonl"
        outbox.write_bytes(b"")
        assert list(read_complete_lines(0, outbox)) == []

    def test_missing_file_yields_nothing(self, tmp_path: Path) -> None:
        assert list(read_complete_lines(0, tmp_path / "no.jsonl")) == []

    def test_complete_line_yields_text_and_next_offset(self, tmp_path: Path) -> None:
        outbox = tmp_path / "outbox.jsonl"
        data = b'{"a":1}\n'
        outbox.write_bytes(data)
        results = list(read_complete_lines(0, outbox))
        assert len(results) == 1
        text, offset = results[0]
        assert text == '{"a":1}'
        assert offset == len(data)

    def test_partial_line_not_yielded(self, tmp_path: Path) -> None:
        outbox = tmp_path / "outbox.jsonl"
        outbox.write_bytes(b'{"a":1}\npartial')
        results = list(read_complete_lines(0, outbox))
        assert len(results) == 1
        assert results[0][1] == len(b'{"a":1}\n')

    def test_start_offset_skips_bytes(self, tmp_path: Path) -> None:
        outbox = tmp_path / "outbox.jsonl"
        line1 = b'{"a":1}\n'
        line2 = b'{"b":2}\n'
        outbox.write_bytes(line1 + line2)
        results = list(read_complete_lines(len(line1), outbox))
        assert len(results) == 1
        assert results[0][0] == '{"b":2}'

    def test_offset_beyond_eof_yields_nothing(self, tmp_path: Path) -> None:
        outbox = tmp_path / "outbox.jsonl"
        outbox.write_bytes(b'{"a":1}\n')
        assert list(read_complete_lines(9999, outbox)) == []


# ---------------------------------------------------------------------------
# transform.py
# ---------------------------------------------------------------------------


class TestTransform:
    def test_success_row_yields_one_event(self) -> None:
        events = outbox_row_to_events(_row())
        assert len(events) == 1
        assert events[0][0] == "session.outcome"

    def test_row_with_patterns_yields_two_events(self) -> None:
        events = outbox_row_to_events(_row(injected_pattern_ids=["auto-aaa"]))
        assert len(events) == 2
        assert events[0][0] == "session.outcome"
        assert events[1][0] == "utilization.scoring.requested"

    def test_session_outcome_payload_shape_success(self) -> None:
        r = _row()
        events = outbox_row_to_events(r)
        _, payload = events[0]
        assert payload["session_id"] == r["conversation_id"]
        assert payload["outcome"] == r["session_outcome"]
        assert payload["reason"] == r["session_outcome_reason"]
        assert payload["correlation_id"] == r["correlation_id"]
        assert payload["matched_agent"] == r["matched_agent"]
        assert payload["matched_confidence"] == r["matched_confidence"]
        assert payload["files_edited"] == r["files_edited"]
        assert payload["started_at"] == r["started_at"]
        assert payload["ended_at"] == r["ended_at"]
        assert payload["error"] is None

    def test_session_outcome_error_on_failed(self) -> None:
        r = _row(session_outcome="failed", session_outcome_reason="traceback found")
        _, payload = outbox_row_to_events(r)[0]
        assert payload["error"] is not None
        assert payload["error"]["code"] == "session_failed"
        assert payload["error"]["component"] == "omnicursor"
        assert payload["error"]["message"] == "traceback found"

    @pytest.mark.parametrize("outcome", ["abandoned", "unknown"])
    def test_session_outcome_error_none_for_non_failed(self, outcome: str) -> None:
        r = _row(session_outcome=outcome)
        _, payload = outbox_row_to_events(r)[0]
        assert payload["error"] is None

    def test_utilization_payload_shape(self) -> None:
        ids = ["auto-aaa", "auto-bbb"]
        r = _row(injected_pattern_ids=ids)
        events = outbox_row_to_events(r)
        _, payload = events[1]
        assert payload["session_id"] == r["conversation_id"]
        assert payload["correlation_id"] == r["correlation_id"]
        assert payload["session_outcome"] == r["session_outcome"]
        assert payload["injected_pattern_ids"] == ids

    def test_empty_injected_pattern_ids_yields_one_event(self) -> None:
        events = outbox_row_to_events(_row(injected_pattern_ids=[]))
        assert len(events) == 1

    def test_legacy_row_without_injected_pattern_ids_yields_one_event(self) -> None:
        """Legacy rows may omit the key; treat like empty — no utilization event."""
        r = _row()
        del r["injected_pattern_ids"]
        events = outbox_row_to_events(r)
        assert len(events) == 1
        assert events[0][0] == "session.outcome"

    def test_missing_required_field_raises_key_error(self) -> None:
        r = _row()
        del r["conversation_id"]
        with pytest.raises(KeyError):
            outbox_row_to_events(r)


# ---------------------------------------------------------------------------
# publisher.py
# ---------------------------------------------------------------------------


class TestNoopPublisher:
    def test_publish_returns_true(self) -> None:
        pub = NoopPublisher()
        assert pub.publish("session.outcome", {"session_id": "x"}) is True

    def test_publish_records_event(self) -> None:
        pub = NoopPublisher()
        pub.publish("session.outcome", {"session_id": "x"})
        assert len(pub.events) == 1
        assert pub.events[0][0] == "session.outcome"

    def test_multiple_publishes_recorded_in_order(self) -> None:
        pub = NoopPublisher()
        pub.publish("session.outcome", {"a": 1})
        pub.publish("utilization.scoring.requested", {"b": 2})
        types = [e for e, _ in pub.events]
        assert types == ["session.outcome", "utilization.scoring.requested"]


# ---------------------------------------------------------------------------
# loop.py / drain_once end-to-end
# ---------------------------------------------------------------------------


class TestDrainOnce:
    def test_empty_outbox(self, tmp_path: Path) -> None:
        outbox = tmp_path / "outbox.jsonl"
        outbox.write_bytes(b"")
        cursor = tmp_path / "outbox.cursor"
        pub = NoopPublisher()
        stats = drain_once(pub, outbox_path=outbox, cursor_path=cursor)
        assert len(pub.events) == 0
        assert stats["rows_processed"] == 0
        assert stats["events_published"] == 0
        assert read_offset(cursor) == 0

    def test_missing_outbox(self, tmp_path: Path) -> None:
        cursor = tmp_path / "outbox.cursor"
        pub = NoopPublisher()
        stats = drain_once(pub, outbox_path=tmp_path / "no.jsonl", cursor_path=cursor)
        assert len(pub.events) == 0
        assert stats["rows_processed"] == 0

    def test_valid_line_without_patterns_one_event(self, tmp_path: Path) -> None:
        outbox = tmp_path / "outbox.jsonl"
        cursor = tmp_path / "outbox.cursor"
        _write_outbox(outbox, [_row()])
        pub = NoopPublisher()
        drain_once(pub, outbox_path=outbox, cursor_path=cursor)
        assert len(pub.events) == 1
        assert pub.events[0][0] == "session.outcome"

    def test_valid_line_with_patterns_two_events(self, tmp_path: Path) -> None:
        outbox = tmp_path / "outbox.jsonl"
        cursor = tmp_path / "outbox.cursor"
        _write_outbox(outbox, [_row(injected_pattern_ids=["auto-aaa", "auto-bbb"])])
        pub = NoopPublisher()
        drain_once(pub, outbox_path=outbox, cursor_path=cursor)
        assert len(pub.events) == 2
        types = [e for e, _ in pub.events]
        assert types == ["session.outcome", "utilization.scoring.requested"]

    def test_invalid_json_advances_cursor(self, tmp_path: Path) -> None:
        outbox = tmp_path / "outbox.jsonl"
        cursor = tmp_path / "outbox.cursor"
        poison = b"not valid json\n"
        valid_row = json.dumps(_row(conversation_id="conv-2"), separators=(",", ":")).encode() + b"\n"
        outbox.write_bytes(poison + valid_row)
        pub = NoopPublisher()
        stats = drain_once(pub, outbox_path=outbox, cursor_path=cursor)
        assert stats["rows_skipped"] == 1
        assert stats["rows_processed"] == 1
        assert len(pub.events) == 1
        assert read_offset(cursor) == len(poison) + len(valid_row)

    def test_partial_line_does_not_advance_cursor(self, tmp_path: Path) -> None:
        outbox = tmp_path / "outbox.jsonl"
        cursor = tmp_path / "outbox.cursor"
        complete = json.dumps(_row(conversation_id="conv-A"), separators=(",", ":")).encode() + b"\n"
        # Split a second valid row mid-bytes so we have a partial line without \n.
        second_full = json.dumps(_row(conversation_id="conv-B"), separators=(",", ":")).encode() + b"\n"
        partial = second_full[: len(second_full) // 2]
        outbox.write_bytes(complete + partial)
        pub = NoopPublisher()
        drain_once(pub, outbox_path=outbox, cursor_path=cursor)
        # Cursor advances only past the complete line; partial is untouched.
        assert read_offset(cursor) == len(complete)
        assert len(pub.events) == 1
        # Write the remainder of the second row and re-drain.
        with outbox.open("ab") as f:
            f.write(second_full[len(partial):])
        pub2 = NoopPublisher()
        drain_once(pub2, outbox_path=outbox, cursor_path=cursor)
        assert len(pub2.events) == 1

    def test_publisher_failure_does_not_advance_cursor(self, tmp_path: Path) -> None:
        outbox = tmp_path / "outbox.jsonl"
        cursor = tmp_path / "outbox.cursor"
        _write_outbox(outbox, [_row()])
        stats = drain_once(_FailingPublisher(), outbox_path=outbox, cursor_path=cursor)
        assert stats["rows_failed_publish"] == 1
        assert read_offset(cursor) == 0
        # Retry with a working publisher.
        pub = _RecordingPublisher()
        drain_once(pub, outbox_path=outbox, cursor_path=cursor)
        assert len(pub.events) == 1

    def test_second_drain_does_not_duplicate_events(self, tmp_path: Path) -> None:
        outbox = tmp_path / "outbox.jsonl"
        cursor = tmp_path / "outbox.cursor"
        _write_outbox(outbox, [_row()])
        pub = NoopPublisher()
        drain_once(pub, outbox_path=outbox, cursor_path=cursor)
        first_count = len(pub.events)
        drain_once(pub, outbox_path=outbox, cursor_path=cursor)
        assert len(pub.events) == first_count  # no new events

    def test_corrupt_cursor_falls_back_to_zero(self, tmp_path: Path) -> None:
        outbox = tmp_path / "outbox.jsonl"
        cursor = tmp_path / "outbox.cursor"
        _write_outbox(outbox, [_row()])
        cursor.write_text("garbage\n")
        pub = NoopPublisher()
        drain_once(pub, outbox_path=outbox, cursor_path=cursor)
        assert len(pub.events) == 1  # full drain from byte 0

    def test_raising_publisher_does_not_propagate(self, tmp_path: Path) -> None:
        outbox = tmp_path / "outbox.jsonl"
        cursor = tmp_path / "outbox.cursor"
        _write_outbox(outbox, [_row()])
        stats = drain_once(_RaisingPublisher(), outbox_path=outbox, cursor_path=cursor)
        assert stats["rows_failed_publish"] == 1
        assert read_offset(cursor) == 0

    def test_raising_publisher_row_retried_by_working_publisher(self, tmp_path: Path) -> None:
        outbox = tmp_path / "outbox.jsonl"
        cursor = tmp_path / "outbox.cursor"
        _write_outbox(outbox, [_row()])
        drain_once(_RaisingPublisher(), outbox_path=outbox, cursor_path=cursor)
        pub = _RecordingPublisher()
        drain_once(pub, outbox_path=outbox, cursor_path=cursor)
        assert len(pub.events) == 1

    def test_drain_returns_stats_keys(self, tmp_path: Path) -> None:
        outbox = tmp_path / "outbox.jsonl"
        cursor = tmp_path / "outbox.cursor"
        _write_outbox(outbox, [_row(injected_pattern_ids=["auto-x"])])
        stats = drain_once(NoopPublisher(), outbox_path=outbox, cursor_path=cursor)
        expected_keys = {
            "rows_processed",
            "events_published",
            "rows_skipped",
            "rows_failed_publish",
            "final_offset",
        }
        assert expected_keys == set(stats.keys())
        assert stats["rows_processed"] == 1
        assert stats["events_published"] == 2  # session.outcome + utilization
        assert stats["rows_skipped"] == 0
        assert stats["rows_failed_publish"] == 0
