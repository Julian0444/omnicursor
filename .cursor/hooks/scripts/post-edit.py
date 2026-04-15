"""afterFileEdit hook — post-edit diagnostics and event logging.

Node contract: ``node_cursor_file_edit_effect``
(``src/omnicursor/nodes/node_cursor_file_edit_effect/contract.yaml``).

Port of on_edit.py to the scripts/ layer with:
  - Shared lib (lib/_common.py) via sys.path
  - Correlation threading: reads latest_correlation_id from current.json
  - Typed event schema: event, conversation_id, correlation_id, file_path,
    edit_count, language, ruff_findings, hook_duration_ms
  - Ruff diagnostic — never --fix, never modifies files

Informational only — Cursor ignores stdout. Always exits cleanly.
"""

from __future__ import annotations

import datetime
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from _common import (
    OMNICURSOR_DIR,
    ensure_dirs,
    log_event,
    read_session_context,
    read_stdin,
    write_stdout,
)


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

_EXTENSION_MAP: Dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".md": "markdown",
}


def detect_language(path: str) -> str:
    """Return a language label based on file extension."""
    ext = Path(path).suffix.lower()
    return _EXTENSION_MAP.get(ext, "other")


# ---------------------------------------------------------------------------
# Ruff diagnostics — read-only, never --fix
# ---------------------------------------------------------------------------

LINT_LOG = OMNICURSOR_DIR / "lint.jsonl"


def run_ruff_check(file_path: str) -> int:
    """Run ``ruff check`` diagnostically on *file_path*.

    Returns the number of findings (lines of output). Logs a JSONL entry to
    ``~/.omnicursor/lint.jsonl`` only when findings exist.

    Never passes ``--fix``. Never modifies any file.
    """
    try:
        result = subprocess.run(
            ["ruff", "check", file_path],
            capture_output=True,
            text=True,
            timeout=5,
        )
        output = (result.stdout or "").strip()
        # Each non-empty output line is one finding
        findings = len([ln for ln in output.splitlines() if ln.strip()])
        if findings:
            ensure_dirs()
            entry = {
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "file_path": file_path,
                "findings": findings,
                "output": output[:2000],
                "returncode": result.returncode,
            }
            with LINT_LOG.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry) + "\n")
        return findings
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        # ruff not installed, timed out, or I/O error — skip silently
        return 0


# ---------------------------------------------------------------------------
# Edit handler
# ---------------------------------------------------------------------------


def handle_edit(event: Dict[str, Any]) -> Dict[str, Any]:
    """Process an afterFileEdit event.

    Detects language, optionally runs ruff (Python only), and returns a
    partial event dict. ``main()`` enriches this with ``correlation_id``
    and ``hook_duration_ms`` before logging.
    """
    file_path = event.get("file_path", "")
    edits = event.get("edits", [])
    conversation_id = event.get("conversation_id", "")

    language = detect_language(file_path) if file_path else "other"
    edit_count = len(edits) if isinstance(edits, list) else 0

    ruff_findings = 0
    if language == "python" and file_path:
        ruff_findings = run_ruff_check(file_path)

    return {
        "event": "file_edited",
        "conversation_id": conversation_id,
        "file_path": file_path[:500] if file_path else "",
        "edit_count": edit_count,
        "language": language,
        "ruff_findings": ruff_findings,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    _start = time.monotonic()
    try:
        data = read_stdin()
        session = read_session_context()
        correlation_id: str = session.get("latest_correlation_id", "")

        result = handle_edit(data)
        hook_ms = int((time.monotonic() - _start) * 1000)

        log_event({
            **result,
            "correlation_id": correlation_id,
            "hook_duration_ms": hook_ms,
        })
    except Exception:
        pass
    write_stdout({})


if __name__ == "__main__":
    main()
