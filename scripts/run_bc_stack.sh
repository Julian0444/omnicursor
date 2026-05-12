#!/usr/bin/env bash
# Starts the full Option B+C stack:
#   1. Docker Compose (Redpanda + Postgres + Valkey + omniintelligence services)
#   2. OmniCursor sidecar (socket → outbox → Kafka)
#
# Usage:
#   bash scripts/run_bc_stack.sh             # default: kafka publisher
#   bash scripts/run_bc_stack.sh --noop      # use noop publisher (no Kafka writes)
#   bash scripts/run_bc_stack.sh --down      # stop the compose stack and exit
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Resolve venv — worktrees share the parent repo's .venv
if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
    PYTHON="$REPO_ROOT/.venv/bin/python"
else
    MAIN_ROOT="$(cd "$REPO_ROOT/../.." && pwd)"
    PYTHON="$MAIN_ROOT/.venv/bin/python"
fi

PUBLISHER="kafka"

for arg in "$@"; do
    case "$arg" in
        --noop) PUBLISHER="noop" ;;
        --down)
            echo "Stopping compose stack..."
            docker compose -f "$REPO_ROOT/compose.yaml" down
            exit 0
            ;;
    esac
done

# --- 1. Start compose stack ---
echo "Starting compose stack (Redpanda + Postgres + Valkey + omniintelligence)..."
docker compose -f "$REPO_ROOT/compose.yaml" up -d

echo ""
echo "Waiting for intelligence-reducer to be healthy..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:18091/health >/dev/null 2>&1; then
        echo "intelligence-reducer is healthy."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "WARNING: intelligence-reducer not healthy after 60s — proceeding anyway."
        echo "         Check 'docker compose logs intelligence-reducer' if patterns don't sync."
    fi
    sleep 2
done

# --- 2. Start sidecar ---
echo ""
echo "Starting OmniCursor sidecar (publisher=$PUBLISHER)..."
echo "  INTELLIGENCE_SERVICE_URL=http://localhost:18091"
echo "  OMNICURSOR_PATTERN_SYNC_HTTP=1"
echo ""

export INTELLIGENCE_SERVICE_URL=http://localhost:18091
export OMNICURSOR_PATTERN_SYNC_HTTP=1
export KAFKA_BOOTSTRAP_SERVERS=localhost:19092

# --- 3. Start OmniDash bridge (optional) ---
if [ -n "${OMNIDASH_ROOT:-}" ] && [ -d "$OMNIDASH_ROOT" ]; then
    echo "Starting OmniDash bridge (fixtures → ${OMNIDASH_FIXTURES_DIR:-/tmp/omnicursor-omnidash-fixtures})..."
    "$PYTHON" -m omnicursor.drainer.omnidash_bridge \
        --outbox ~/.omnicursor/outbox.jsonl \
        --cursor ~/.omnicursor/omnidash.cursor \
        --fixtures "${OMNIDASH_FIXTURES_DIR:-/tmp/omnicursor-omnidash-fixtures}" \
        --interval 2 &
    OMNIDASH_PID=$!
    echo "  OmniDash bridge PID=$OMNIDASH_PID"
    trap "kill $OMNIDASH_PID 2>/dev/null; docker compose -f \"$REPO_ROOT/compose.yaml\" down" EXIT
fi

exec "$PYTHON" -m omnicursor.sidecar.daemon \
    --publisher "$PUBLISHER" \
    --outbox ~/.omnicursor/outbox.jsonl \
    --socket ~/.omnicursor/emit.sock \
    --interval 2.0
