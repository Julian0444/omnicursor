"""Outbox reader — yields complete newline-terminated lines from a byte offset (stdlib only).

Partial final lines (no trailing newline) are never yielded, so the cursor
never advances past an incomplete JSON record.  Each yielded item is a tuple
of (line_text: str, next_byte_offset: int) where next_byte_offset is the
position immediately after the terminating newline.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator, Optional, Tuple


def _default_outbox_path() -> Path:
    env = os.environ.get("OMNICURSOR_OUTBOX_FILE")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".omnicursor" / "outbox.jsonl"


def read_complete_lines(
    start_offset: int,
    outbox_path: Optional[Path] = None,
) -> Iterator[Tuple[str, int]]:
    """Yield (line_text, byte_offset_after_line) for every complete line.

    Opens the outbox in binary mode, seeks to start_offset, then reads to EOF.
    Only lines that end with b'\\n' are yielded — the partial trailing chunk
    (if any) is silently ignored so the cursor never advances past an
    incomplete record.

    If start_offset is at or beyond EOF, yields nothing without error.
    """
    path = outbox_path if outbox_path is not None else _default_outbox_path()
    if not path.exists():
        return

    try:
        with path.open("rb") as f:
            f.seek(start_offset)
            current_offset = start_offset
            for raw_line in f:
                if not raw_line.endswith(b"\n"):
                    # Partial line — stop; do not advance past it.
                    break
                next_offset = current_offset + len(raw_line)
                line_text = raw_line.decode("utf-8", errors="replace").rstrip("\n")
                yield line_text, next_offset
                current_offset = next_offset
    except OSError:
        return
