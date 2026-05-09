"""Fetch learned patterns from omniintelligence into learned_patterns.json.

Used by tests and optional tooling. Hooks invoke the stdlib copy in
``.cursor/hooks/lib/pattern_sync.py`` only when ``OMNICURSOR_PATTERN_SYNC_HTTP`` is set
(dev / experimentation — not the default capstone path).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional


def _read_local_patterns(path: Path) -> list[Any]:
    """Read local patterns file and return a normalized list."""
    try:
        if not path.exists():
            return []
        body: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return []

    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        patterns = body.get("patterns")
        if isinstance(patterns, list):
            return patterns
    return []


def _patterns_from_response(body: Any) -> list[Any]:
    """Normalize /api/v1/patterns response body into a list."""
    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        patterns = body.get("patterns")
        if isinstance(patterns, list):
            return patterns
    return []


def _pattern_identity(pattern: Any) -> str:
    """Best-effort stable identity for de-duplication."""
    if isinstance(pattern, dict):
        pattern_id = pattern.get("pattern_id")
        if isinstance(pattern_id, str) and pattern_id:
            return f"pattern_id:{pattern_id}"
    try:
        return f"json:{json.dumps(pattern, sort_keys=True, ensure_ascii=False)}"
    except (TypeError, ValueError):
        return f"repr:{repr(pattern)}"


def _merge_patterns(local_patterns: list[Any], remote_patterns: list[Any]) -> list[Any]:
    """Keep local patterns and append only new remote patterns."""
    merged = list(local_patterns)
    seen = {_pattern_identity(item) for item in local_patterns}
    for pattern in remote_patterns:
        identity = _pattern_identity(pattern)
        if identity in seen:
            continue
        merged.append(pattern)
        seen.add(identity)
    return merged


def run(
    target_file: Optional[Path] = None,
    *,
    base_url: Optional[str] = None,
    timeout_s: float = 3.0,
) -> bool:
    """Merge local patterns with GET /api/v1/patterns and write output.

    Returns True if remote patterns were fetched and merged.
    """
    path = target_file or (Path.home() / ".omnicursor" / "learned_patterns.json")
    local_patterns = _read_local_patterns(path)
    base = (base_url or os.environ.get("OMNIINTELLIGENCE_URL") or "http://127.0.0.1:18091").rstrip(
        "/"
    )
    url = f"{base}/api/v1/patterns"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
        body: Any = json.loads(raw)
        remote_patterns = _patterns_from_response(body)
        normalized: dict[str, Any] = {"patterns": _merge_patterns(local_patterns, remote_patterns)}
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(
            json.dumps(normalized, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp, path)
        return True
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TypeError):
        return False
