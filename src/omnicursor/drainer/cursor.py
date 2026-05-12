"""Byte-offset cursor for the outbox drainer (stdlib only).

Stores the number of bytes already consumed from outbox.jsonl as a plain
base-10 integer in ~/.omnicursor/outbox.cursor.  Atomic write via mkstemp +
os.replace mirrors the pattern used by pattern_writer._save_patterns and
pattern_sync.run.  A corrupt or missing cursor silently falls back to 0.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional


def _default_cursor_path() -> Path:
    return Path.home() / ".omnicursor" / "outbox.cursor"


def _resolve(path: Optional[Path]) -> Path:
    return path if path is not None else _default_cursor_path()


def read_offset(path: Optional[Path] = None) -> int:
    """Return the stored byte offset, or 0 on any error / corruption."""
    p = _resolve(path)
    try:
        raw = p.read_text(encoding="utf-8").strip()
        value = int(raw)
        if value < 0:
            return 0
        return value
    except (OSError, ValueError, OverflowError):
        return 0


def write_offset(offset: int, path: Optional[Path] = None) -> bool:
    """Atomically write *offset* to the cursor file.

    Returns True on success, False on any I/O error.  Never raises.
    """
    p = _resolve(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        content = f"{offset}\n"
        fd, tmp_name = tempfile.mkstemp(
            prefix=p.name + ".",
            suffix=".tmp",
            dir=str(p.parent),
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, p)
        except Exception:
            try:
                tmp_path.unlink()
            except OSError:
                pass
            raise
        return True
    except Exception:
        return False
