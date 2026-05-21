"""beforeShellExecution hook — two-tier shell command guard.

This hook CAN control execution. Returns deny to block, allow to proceed.

Node contract: ``node_cursor_shell_guard_effect``
(``src/omnicursor/nodes/node_cursor_shell_guard_effect/contract.yaml``).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

# Upper bound for denied-command audit logs (avoid multi-megabyte JSONL rows).
_MAX_DENIED_COMMAND_LOG_CHARS = 65536

_hooks = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_hooks / "lib"))
sys.path.insert(0, str(_hooks.parent.parent / "src"))

from _common import (  # noqa: E402
    SESSIONS_DIR,
    log_event,
    read_session_context,
    read_stdin,
    write_stdout,
)
from omnicursor.shell_guard import guard_command as _guard_command_impl  # noqa: E402

_DOD_CONFIG_PATH: Path = _hooks / "config" / "dod_enforcement.json"


def guard_command(command: str, *, conversation_id: str = "", sessions_root=None):
    """Hook-local wrapper that injects the DoD config path."""
    return _guard_command_impl(
        command,
        conversation_id=conversation_id,
        sessions_root=sessions_root,
        dod_config_path=_DOD_CONFIG_PATH,
    )


def main() -> None:
    _start = time.monotonic()
    try:
        data = read_stdin()
        command = data.get("command", "")
        conversation_id = data.get("conversation_id", "")

        session = read_session_context()
        correlation_id: str = session.get("latest_correlation_id", "")

        response = guard_command(command, conversation_id=conversation_id, sessions_root=SESSIONS_DIR)

        if response.get("permission") == "deny":
            decision = "deny"
            reason = response.get("userMessage", "")
        elif "agentMessage" in response:
            decision = "warn"
            reason = response.get("agentMessage", "")
        else:
            decision = "allow"
            reason = ""

        hook_ms = int((time.monotonic() - _start) * 1000)

        cmd_truncated = False
        if decision == "deny":
            if len(command) > _MAX_DENIED_COMMAND_LOG_CHARS:
                logged_command = command[:_MAX_DENIED_COMMAND_LOG_CHARS]
                cmd_truncated = True
            else:
                logged_command = command
        else:
            logged_command = command[:500]

        payload: dict[str, Any] = {
            "event": "shell_guard",
            "conversation_id": conversation_id,
            "correlation_id": correlation_id,
            "command": logged_command,
            "decision": decision,
            "reason": reason,
            "hook_duration_ms": hook_ms,
        }
        if decision == "deny":
            payload["permission_denied"] = True
        if cmd_truncated:
            payload["command_truncated"] = True
        log_event(payload)

        write_stdout(response)
    except Exception:
        write_stdout({"permission": "allow"})


if __name__ == "__main__":
    main()
