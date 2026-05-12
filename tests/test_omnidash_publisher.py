"""Tests for src/omnicursor/drainer/omnidash_publisher.py and omnidash_bridge.py."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict
from unittest.mock import patch

import omnicursor.drainer.omnidash_publisher as pub_mod
from omnicursor.drainer.omnidash_bridge import main as bridge_main
from omnicursor.drainer.omnidash_publisher import TOPIC, OmniDashFixturePublisher


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_OUTCOME_PAYLOAD: Dict = {
    "session_id": "s1",
    "outcome": "success",
    "reason": "completion markers found",
    "correlation_id": "corr-1",
    "matched_agent": "debugging",
    "matched_confidence": 0.9,
    "files_edited": 3,
    "started_at": "2026-05-11T10:00:00Z",
    "ended_at": "2026-05-11T10:05:00Z",
    "error": None,
}

_UTIL_PAYLOAD: Dict = {
    "session_id": "s1",
    "correlation_id": "corr-1",
    "session_outcome": "success",
    "injected_pattern_ids": ["auto-aaa", "auto-bbb"],
}


def _topic_dir(fixtures: Path) -> Path:
    return fixtures / TOPIC


def _read_index(fixtures: Path) -> list:
    return json.loads((_topic_dir(fixtures) / "index.json").read_text())


def _read_event(fixtures: Path, filename: str) -> Dict:
    return json.loads((_topic_dir(fixtures) / filename).read_text())


# ---------------------------------------------------------------------------
# OmniDashFixturePublisher
# ---------------------------------------------------------------------------


class TestOmniDashFixturePublisher:
    def test_publish_session_outcome_writes_files(self, tmp_path: Path) -> None:
        pub = OmniDashFixturePublisher(fixtures_dir=tmp_path)
        assert pub.publish("session.outcome", _OUTCOME_PAYLOAD) is True
        assert (_topic_dir(tmp_path) / "index.json").exists()
        assert (_topic_dir(tmp_path) / "0.json").exists()

    def test_index_json_references_event_files(self, tmp_path: Path) -> None:
        pub = OmniDashFixturePublisher(fixtures_dir=tmp_path)
        pub.publish("session.outcome", _OUTCOME_PAYLOAD)
        assert _read_index(tmp_path) == ["0.json"]
        pub.publish("utilization.scoring.requested", _UTIL_PAYLOAD)
        assert _read_index(tmp_path) == ["0.json", "1.json"]

    def test_event_row_has_required_keys(self, tmp_path: Path) -> None:
        pub = OmniDashFixturePublisher(fixtures_dir=tmp_path)
        pub.publish("session.outcome", _OUTCOME_PAYLOAD)
        event = _read_event(tmp_path, "0.json")
        assert set(event.keys()) == {"id", "type", "timestamp", "source", "topic", "summary", "payload"}

    def test_session_outcome_success_is_action(self, tmp_path: Path) -> None:
        pub = OmniDashFixturePublisher(fixtures_dir=tmp_path)
        pub.publish("session.outcome", {**_OUTCOME_PAYLOAD, "outcome": "success"})
        assert _read_event(tmp_path, "0.json")["type"] == "ACTION"

    def test_session_outcome_failed_is_error(self, tmp_path: Path) -> None:
        pub = OmniDashFixturePublisher(fixtures_dir=tmp_path)
        pub.publish("session.outcome", {**_OUTCOME_PAYLOAD, "outcome": "failed"})
        assert _read_event(tmp_path, "0.json")["type"] == "ERROR"

    def test_session_outcome_abandoned_is_transformation(self, tmp_path: Path) -> None:
        pub = OmniDashFixturePublisher(fixtures_dir=tmp_path)
        pub.publish("session.outcome", {**_OUTCOME_PAYLOAD, "outcome": "abandoned"})
        assert _read_event(tmp_path, "0.json")["type"] == "TRANSFORMATION"

    def test_utilization_scoring_is_transformation(self, tmp_path: Path) -> None:
        pub = OmniDashFixturePublisher(fixtures_dir=tmp_path)
        pub.publish("utilization.scoring.requested", _UTIL_PAYLOAD)
        assert _read_event(tmp_path, "0.json")["type"] == "TRANSFORMATION"

    def test_multiple_publishes_accumulate(self, tmp_path: Path) -> None:
        pub = OmniDashFixturePublisher(fixtures_dir=tmp_path)
        pub.publish("session.outcome", _OUTCOME_PAYLOAD)
        pub.publish("session.outcome", _OUTCOME_PAYLOAD)
        pub.publish("utilization.scoring.requested", _UTIL_PAYLOAD)
        assert len(_read_index(tmp_path)) == 3

    def test_trim_oldest_after_max_live_events(self, tmp_path: Path) -> None:
        pub = OmniDashFixturePublisher(fixtures_dir=tmp_path, max_live_events=5)
        # Publish 7 events with distinct timestamps (sleep ensures ordering).
        ids = []
        for i in range(7):
            payload = {**_OUTCOME_PAYLOAD, "session_id": f"s{i}"}
            pub.publish("session.outcome", payload)
            ids.append(pub._live_events[0]["id"])  # most-recent id after each append
            if i < 6:
                time.sleep(0.01)  # ensure timestamp ordering
        assert len(_read_index(tmp_path)) == 5
        # The 5 surviving events are the 5 most recent — verify via the id
        # stored in 0.json (newest after sort-desc).
        first_in_list = _read_event(tmp_path, "0.json")["id"]
        # The very last published event should be first (newest-first sort).
        assert first_in_list == pub._live_events[0]["id"]

    def test_non_existent_fixtures_dir_is_created(self, tmp_path: Path) -> None:
        deep = tmp_path / "a" / "b" / "c"
        pub = OmniDashFixturePublisher(fixtures_dir=deep)
        assert pub.publish("session.outcome", _OUTCOME_PAYLOAD) is True
        assert (deep / TOPIC / "index.json").exists()

    def test_write_failure_returns_false_and_does_not_raise(self, tmp_path: Path) -> None:
        pub = OmniDashFixturePublisher(fixtures_dir=tmp_path)
        with patch.object(pub_mod.os, "replace", side_effect=OSError("mocked")):
            result = pub.publish("session.outcome", _OUTCOME_PAYLOAD)
        assert result is False

    def test_payload_field_is_json_string(self, tmp_path: Path) -> None:
        pub = OmniDashFixturePublisher(fixtures_dir=tmp_path)
        pub.publish("session.outcome", _OUTCOME_PAYLOAD)
        event = _read_event(tmp_path, "0.json")
        assert isinstance(event["payload"], str)
        assert json.loads(event["payload"]) == _OUTCOME_PAYLOAD

    def test_atomic_write_never_leaves_partial_file(self, tmp_path: Path) -> None:
        pub = OmniDashFixturePublisher(fixtures_dir=tmp_path)
        pub.publish("session.outcome", _OUTCOME_PAYLOAD)
        v1 = _read_index(tmp_path)

        original_replace = pub_mod.os.replace

        def _fail_on_index(src: str, dst: str) -> None:
            if Path(dst).name == "index.json":
                raise OSError("mocked index.json failure")
            return original_replace(src, dst)  # type: ignore[return-value]

        with patch.object(pub_mod.os, "replace", side_effect=_fail_on_index):
            result = pub.publish("session.outcome", _OUTCOME_PAYLOAD)

        assert result is False
        assert _read_index(tmp_path) == v1

    def test_topic_label_uses_dashed_event_type(self, tmp_path: Path) -> None:
        pub = OmniDashFixturePublisher(fixtures_dir=tmp_path)
        pub.publish("session.outcome", _OUTCOME_PAYLOAD)
        event = _read_event(tmp_path, "0.json")
        assert event["topic"] == "onex.evt.omnicursor.session-outcome.v1"

    def test_summary_for_session_outcome_includes_agent_and_files(self, tmp_path: Path) -> None:
        pub = OmniDashFixturePublisher(fixtures_dir=tmp_path)
        pub.publish("session.outcome", _OUTCOME_PAYLOAD)
        summary = _read_event(tmp_path, "0.json")["summary"]
        assert "debugging" in summary
        assert "3" in summary

    def test_summary_for_utilization_lists_pattern_count(self, tmp_path: Path) -> None:
        pub = OmniDashFixturePublisher(fixtures_dir=tmp_path)
        pub.publish("utilization.scoring.requested", _UTIL_PAYLOAD)
        summary = _read_event(tmp_path, "0.json")["summary"]
        assert "2 patterns" in summary


# ---------------------------------------------------------------------------
# omnidash_bridge CLI
# ---------------------------------------------------------------------------

_VALID_ROW = json.dumps(
    {
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
    },
    separators=(",", ":"),
)


class TestOmniDashBridge:
    def test_bridge_main_once_drains_outbox(self, tmp_path: Path) -> None:
        outbox = tmp_path / "outbox.jsonl"
        outbox.write_text(_VALID_ROW + "\n")
        cursor = tmp_path / "omnidash.cursor"
        fixtures = tmp_path / "fixtures"

        ret = bridge_main(
            [
                "--outbox", str(outbox),
                "--cursor", str(cursor),
                "--fixtures", str(fixtures),
                "--once",
            ]
        )

        assert ret == 0
        assert (fixtures / TOPIC / "index.json").exists()

    def test_bridge_main_keyboard_interrupt_exits_cleanly(self, tmp_path: Path) -> None:
        import omnicursor.drainer.omnidash_bridge as bridge_mod

        def _raise(*a, **kw):  # noqa: ANN002, ANN003
            raise KeyboardInterrupt

        with patch.object(bridge_mod, "drain_once", side_effect=_raise):
            ret = bridge_main(
                [
                    "--outbox", str(tmp_path / "o.jsonl"),
                    "--cursor", str(tmp_path / "o.cursor"),
                    "--fixtures", str(tmp_path / "fixtures"),
                    "--once",
                ]
            )

        assert ret == 0
