# OmniCursor — Full Pipeline

This document describes the end-to-end flow from a user prompt to a merged PR
and back into the intelligence system.

---

## Overview

```
User prompt
  └─► user-prompt-submit.py (hook)
        ├─► GET /api/v1/patterns — omniintelligence (Option B read)
        │     └─► fallback: ~/.omnicursor/learned_patterns.json
        ├─► 3-strategy agent scoring → best-fit agent
        └─► system message injected: agent persona + relevant patterns

/execute-plan typed
  └─► onex:plan-review — adversarial plan check
  └─► onex:plan-to-tickets — Linear tickets created
  └─► run_ticket_pipeline(ticket_id) — omnimarket bridge
        └─► IMPLEMENT → LOCAL_REVIEW → CREATE_PR → TEST_ITERATE
              → CI_WATCH → PR_REVIEW → AUTO_MERGE → DONE

Session ends
  └─► stop.py (hook)
        ├─► outcome classification: success / failed / abandoned / unknown
        ├─► write_session_outcome() → ~/.omnicursor/outbox.jsonl    (Option C durable)
        ├─► send_event("session.outcome") → ~/.omnicursor/emit.sock
        ├─► send_event("utilization.scoring.requested") → socket
        └─► write_session_patterns() → ~/.omnicursor/learned_patterns.json  (Option A)

Sidecar daemon (always running)
  ├─► socket_listener: receives live events, appends to outbox
  └─► drain_loop (2s tick)
        └─► reads outbox → KafkaPublisher                           (Option C emit)
              └─► Redpanda topics:
                    onex.evt.omnicursor.session-outcome.v1
                    onex.cmd.omniintelligence.utilization-scoring.v1

omniintelligence (docker compose stack)
  └─► consumes Kafka events → updates pattern weights in Postgres

Next prompt
  └─► GET /api/v1/patterns returns updated weights → loop closes
```

---

## Stage 1 — Prompt intake (user-prompt-submit.py)

Fires on every prompt before the model sees anything.

**Pattern source priority:**
1. `GET /api/v1/patterns?domain=<X>` from omniintelligence (Option B, 900ms timeout)
2. Local `~/.omnicursor/learned_patterns.json` (fallback, always available)

**Agent scoring — 3 strategies in order:**
1. Exact substring match on `explicit_triggers` → 0.95 confidence
2. Fuzzy match via SequenceMatcher → 0.70–0.80 confidence
3. Keyword overlap on `activation_keywords` → 0.55–0.85 confidence

`HARD_FLOOR = 0.55` — anything below falls back to `polymorphic-agent`.

**Output:** a `{"systemMessage": "..."}` block containing:
- HTML comment header with agent name, confidence, pattern count, correlation ID
- Agent persona and instructions
- Relevance-filtered learned patterns (max 10, scored by keyword overlap)
- Delegation rule (if prompt complexity exceeds threshold)
- Once-per-session handoff nudge (for long unstructured sessions)

---

## Stage 2 — Execution (onex:execute-plan skill)

Triggered when the user types `/execute-plan`. Accepts either a plan file
(`/execute-plan docs/plans/my-plan.md`) or a single ticket ID
(`/execute-plan — implement OMN-XX`).

| Phase | What happens |
|---|---|
| Plan review | `onex:plan-review` — adversarial check. Stops on CRITICAL/MAJOR findings. Skipped when passing a ticket ID directly. |
| Ticket creation | `onex:plan-to-tickets` — one Linear epic + one ticket per plan task. Skipped when passing a ticket ID directly. |
| Pipeline | `run_ticket_pipeline(ticket_id)` via omnimarket MCP bridge for each ticket. |

**omnimarket `node_ticket_pipeline` phases:**

| Phase | What it does |
|---|---|
| `IMPLEMENT` | Reads ticket, writes code, runs tests |
| `LOCAL_REVIEW` | `node_local_review` — iterative fix loop until clean |
| `CREATE_PR` | `gh pr create` with ticket summary |
| `TEST_ITERATE` | Re-runs tests post-PR, fixes failures (max 3 cycles) |
| `CI_WATCH` | `node_ci_watch` — polls GitHub Actions, auto-fixes CI failures |
| `PR_REVIEW` | Waits for review approval |
| `AUTO_MERGE` | Merges when approved + CI green |
| `DONE` | Marks Linear ticket Done, reports PR number |

Circuit breaker trips after 3 consecutive phase failures.

**Fallback:** if omnimarket bridge is unavailable, `execute-plan` implements inline
(no PR creation, no CI watch) and marks tickets done manually.

---

## Stage 3 — Session end (stop.py)

Fires when the Cursor session ends.

**Outcome classification — 4-gate decision tree:**

| Gate | Condition | Outcome |
|---|---|---|
| 1 | Status maps to failure OR error markers in event text | `failed` |
| 2 | Files edited AND completion markers present | `success` |
| 3 | No completion markers AND duration < 60s | `abandoned` |
| 4 | Catch-all | `unknown` |

**What gets written:**

- `~/.omnicursor/outbox.jsonl` — one JSONL record per session (schema: `omnicursor.session_outcome.v1`)
  - Fields: conversation_id, session_outcome, matched_agent, matched_confidence,
    files_edited, prompts_classified, injected_pattern_ids, timestamps
- `~/.omnicursor/emit.sock` — two socket events:
  - `session.outcome` — outcome + agent + confidence
  - `utilization.scoring.requested` — which pattern IDs were injected
- `~/.omnicursor/learned_patterns.json` — updated weights (Option A local learning)

---

## Stage 4 — Sidecar drain (Option C)

Two concurrent components run in the sidecar daemon:

**socket_listener** — binds `~/.omnicursor/emit.sock`, receives live events from the
stop hook, appends them to the outbox. Handles concurrent writers safely.

**drain_loop** — polls outbox every 2 seconds. For each new row:
- Transforms outbox record into a typed event
- Publishes to Redpanda via `KafkaPublisher`
- Advances the cursor file so rows are not re-published

**Kafka topics published:**

| Event | Topic |
|---|---|
| `session.outcome` | `onex.evt.omnicursor.session-outcome.v1` |
| `session.outcome` | `onex.cmd.omniintelligence.session-outcome.v1` |
| `utilization.scoring.requested` | `onex.cmd.omniintelligence.utilization-scoring.v1` |

**Publisher modes:**
- `--publisher kafka` — production (requires Redpanda running)
- `--publisher noop` — logs only, no side effects (testing)

---

## Stage 5 — Intelligence update (omniintelligence)

omniintelligence runs as a local Docker Compose stack:

| Service | Port | Role |
|---|---|---|
| `intelligence-reducer` | 18091 | Stores pattern weights in Postgres, serves `GET /api/v1/patterns` |
| `intelligence-orchestrator` | 18092 | Workflow coordination |
| `quality-scoring-compute` | 18093 | Quality scoring node |
| `redpanda` | 19092 | Kafka-compatible broker |
| `postgres` | 5436 | Pattern storage |
| `valkey` | 16379 | Cache |

On receiving a `session.outcome` event, omniintelligence updates pattern weights for
the patterns that were injected in that session. Patterns from successful sessions
get higher weights; patterns from failed sessions decay.

---

## Stage 6 — Loop closes (next prompt)

On the next user prompt, `user-prompt-submit.py` calls `GET /api/v1/patterns` and
receives the weights updated by Stage 5. The top-scored patterns for the current
domain are injected into the system message.

**The loop:**
```
prompt → inject patterns → session outcome → Kafka → weights updated → better patterns next prompt
```

Each session improves the context for the next one.

---

## Option dependencies

| Feature | Requires |
|---|---|
| Local pattern learning (A) | Nothing — always on |
| Per-prompt API injection (B read) | `intelligence-reducer` running (`docker compose up`) |
| Session-end pattern sync (B pull) | `OMNICURSOR_PATTERN_SYNC_HTTP=1` + reducer running |
| Outbox + socket emit (C) | Sidecar running (`run_bc_stack.sh` or `run_sidecar.sh`) |
| Kafka publishing (C) | Redpanda running + `--publisher kafka` |
| Full learning loop (A+B+C) | All of the above — `run_bc_stack.sh` starts everything |
| Ticket pipeline with PR | `OMNIMARKET_ROOT` set + omnimarket MCP server running in Cursor |
