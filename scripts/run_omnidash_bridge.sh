#!/usr/bin/env bash
set -euo pipefail

OUTBOX="${OMNICURSOR_OUTBOX_FILE:-$HOME/.omnicursor/outbox.jsonl}"
CURSOR="${OMNICURSOR_BRIDGE_CURSOR:-$HOME/.omnicursor/omnidash.cursor}"
FIXTURES="${OMNIDASH_FIXTURES_DIR:-/tmp/omnicursor-omnidash-fixtures}"
INTERVAL="${OMNICURSOR_BRIDGE_INTERVAL:-2}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$REPO_ROOT/.venv/bin/python" -m omnicursor.drainer.omnidash_bridge \
  --outbox "$OUTBOX" \
  --cursor "$CURSOR" \
  --fixtures "$FIXTURES" \
  --interval "$INTERVAL"
