#!/usr/bin/env bash
# OmniCursor sidecar — outbox drainer + Unix socket listener
#
# Usage:
#   bash scripts/run_sidecar.sh                         # OmniDash mode (default)
#   bash scripts/run_sidecar.sh --publisher kafka       # Kafka/Redpanda mode
#   bash scripts/run_sidecar.sh --publisher noop        # log-only (testing)
#   bash scripts/run_sidecar.sh --once                  # drain once and exit
#
# Environment:
#   KAFKA_BOOTSTRAP_SERVERS   Kafka broker address (default: localhost:29092)
#   OMNICURSOR_OUTBOX_FILE    override outbox path (default: ~/.omnicursor/outbox.jsonl)
#   OMNICURSOR_EMIT_SOCKET    override socket path (default: ~/.omnicursor/emit.sock)
#   OMNIDASH_FIXTURES_DIR     override fixtures dir for omnidash publisher
set -euo pipefail

OUTBOX="${OMNICURSOR_OUTBOX_FILE:-$HOME/.omnicursor/outbox.jsonl}"
SOCKET="${OMNICURSOR_EMIT_SOCKET:-$HOME/.omnicursor/emit.sock}"
CURSOR="${OMNICURSOR_SIDECAR_CURSOR:-$HOME/.omnicursor/sidecar.cursor}"
FIXTURES="${OMNIDASH_FIXTURES_DIR:-/tmp/omnicursor-omnidash-fixtures}"
INTERVAL="${OMNICURSOR_SIDECAR_INTERVAL:-2}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec "$REPO_ROOT/.venv/bin/python" -m omnicursor.sidecar.daemon \
  --outbox "$OUTBOX" \
  --socket "$SOCKET" \
  --cursor "$CURSOR" \
  --fixtures "$FIXTURES" \
  --interval "$INTERVAL" \
  "$@"
