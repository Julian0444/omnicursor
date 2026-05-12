"""Unix socket listener — receives live hook events and appends them to outbox.jsonl.

The stop hook writes to ~/.omnicursor/emit.sock via emit_client.py. This listener
bridges the live (real-time) path to the durable outbox so a single drain loop
can replay all events regardless of whether they arrived live or via the stop hook.

Wire protocol (newline-terminated JSON, matching emit_client.py):
  Request:  {"event_type": "...", "payload": {...}}
  Response: {"status": "queued", "event_id": "..."}
  Ping:     {"command": "ping"}
  Pong:     {"status": "ok"}

Stdlib only. The listener runs in a daemon thread alongside the drain loop.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import threading
import uuid
from pathlib import Path
from typing import Optional

_log = logging.getLogger(__name__)

_DEFAULT_SOCKET = Path.home() / ".omnicursor" / "emit.sock"
_DEFAULT_OUTBOX = Path.home() / ".omnicursor" / "outbox.jsonl"


def _handle_connection(
    conn: socket.socket,
    outbox_path: Path,
    logger: logging.Logger,
) -> None:
    try:
        with conn.makefile("rb") as f:
            raw = f.readline()
        if not raw:
            return
        msg = json.loads(raw.decode("utf-8"))

        if msg.get("command") == "ping":
            reply = json.dumps({"status": "ok"}) + "\n"
            conn.sendall(reply.encode())
            return

        event_type = msg.get("event_type", "")
        payload = msg.get("payload", {})
        event_id = str(uuid.uuid4())

        # Append to outbox so the drain loop can forward it.
        line = json.dumps(
            {"event_type": event_type, "payload": payload},
            separators=(",", ":"),
            ensure_ascii=False,
        ) + "\n"
        try:
            outbox_path.parent.mkdir(parents=True, exist_ok=True)
            with open(outbox_path, "a", encoding="utf-8") as fh:
                fh.write(line)
        except OSError as exc:
            logger.warning("socket_listener: outbox write failed: %s", exc)

        reply = json.dumps({"status": "queued", "event_id": event_id}) + "\n"
        conn.sendall(reply.encode())
    except Exception as exc:
        logger.debug("socket_listener: connection error: %s", exc)
    finally:
        try:
            conn.close()
        except OSError:
            pass


def _serve(
    sock: socket.socket,
    outbox_path: Path,
    stop_event: threading.Event,
    logger: logging.Logger,
) -> None:
    sock.settimeout(1.0)
    while not stop_event.is_set():
        try:
            conn, _ = sock.accept()
        except socket.timeout:
            continue
        except OSError:
            break
        t = threading.Thread(
            target=_handle_connection,
            args=(conn, outbox_path, logger),
            daemon=True,
        )
        t.start()


def start(
    *,
    socket_path: Optional[Path] = None,
    outbox_path: Optional[Path] = None,
    stop_event: Optional[threading.Event] = None,
    logger: Optional[logging.Logger] = None,
) -> threading.Thread:
    """Start the socket listener in a daemon thread. Returns the thread.

    The thread stops when *stop_event* is set or the socket is closed.
    Removes any stale socket file before binding.
    """
    sock_path = socket_path or _DEFAULT_SOCKET
    out_path = outbox_path or _DEFAULT_OUTBOX
    log = logger or _log
    ev = stop_event or threading.Event()

    sock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.unlink(sock_path)
    except FileNotFoundError:
        pass

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.bind(str(sock_path))
        sock.listen(16)
    except OSError as exc:
        log.error("socket_listener: bind failed on %s: %s", sock_path, exc)
        sock.close()
        raise

    log.info("socket_listener: listening on %s", sock_path)
    t = threading.Thread(
        target=_serve,
        args=(sock, out_path, ev, log),
        daemon=True,
        name="omnicursor-socket-listener",
    )
    t.start()
    return t
