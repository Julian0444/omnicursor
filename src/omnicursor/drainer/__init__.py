"""Outbox drainer — reads outbox.jsonl and publishes events via a pluggable Publisher."""

from omnicursor.drainer.cursor import read_offset, write_offset
from omnicursor.drainer.loop import drain_loop, drain_once
from omnicursor.drainer.omnidash_publisher import OmniDashFixturePublisher
from omnicursor.drainer.publisher import NoopPublisher, Publisher
from omnicursor.drainer.reader import read_complete_lines
from omnicursor.drainer.transform import outbox_row_to_events

__all__ = [
    "read_offset",
    "write_offset",
    "read_complete_lines",
    "outbox_row_to_events",
    "Publisher",
    "NoopPublisher",
    "OmniDashFixturePublisher",
    "drain_once",
    "drain_loop",
]
