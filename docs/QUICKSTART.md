# OmniCursor Quickstart

OmniCursor has three layers:

1. **Cursor Rules** (`.cursor/rules/`, 11 `.mdc` files) — behavior surface for routing and interaction
2. **Cursor Hooks** (`.cursor/hooks/`) — 4 hook entrypoints registered in `.cursor/hooks.json`, plus 2 supporting modules (`_common.py`, `pattern_loader.py`). Deterministic, stdlib only, no LLM
3. **MCP Tools** (`src/omnicursor/server.py`, 3 tools) — FastMCP backend for agent routing, skill loading, and compliance checking

## Prerequisites

- Python 3.10 or newer (developed on 3.12)
- A virtual environment for this repo

## Install

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run the MCP server

```bash
source .venv/bin/activate
omnicursor-server
```

The default transport is `stdio`, which is the right starting point for a local Cursor MCP server.

## Use in Cursor

1. Open the repository root, not a parent folder.
2. Confirm the 11 rules under `.cursor/rules/` are visible in Cursor Settings.
3. Register a local MCP server command that runs `omnicursor-server` from this repo's virtual environment.
4. Hooks are automatically active via `.cursor/hooks.json` — no extra configuration needed.
5. Use the rules for brainstorming, planning, ticketing, debugging, PR review, and session handoff.
6. The MCP tools enhance each rule with routing, skill loading, and compliance checking.

## Available MCP Tools

### `get_agent_context(category: str)`

Returns routing context (agent name, instructions, recommended skill) for a given category.

| Category | Agent | Matching Rule | Recommended Skill |
|----------|-------|---------------|-------------------|
| `debugging` | systematic-debugger | 13-systematic-debugging.mdc | systematic-debugging |
| `brainstorming` | brainstorming-guide | 10-brainstorming.mdc | brainstorming |
| `planning` | plan-writer | 11-writing-plans.mdc | writing-plans |
| `ticketing` | ticket-planner | 12-plan-ticket.mdc | plan-ticket |
| Linear create (YAML → issue) | — | 16-create-ticket.mdc | create-ticket |
| Linear consume / close | — | 17-consume-ticket.mdc | consume-ticket |
| `review` | pr-review | 14-pr-review.mdc | pr-review |
| `handoff` | handoff-guide | 15-handoff.mdc | handoff |

Unrecognized categories fall back to `omnicursor-generalist`.

### `invoke_skill(skill_name: str)`

Loads a Markdown skill from the `skills/` directory and returns its content. Includes `consume-ticket` and `create-ticket` (Linear MCP) plus methodology skills: `systematic-debugging`, `brainstorming`, `writing-plans`, `plan-ticket`, `pr-review`, `pr-polish`, `hostile-reviewer`, `defense-in-depth`, `merge-planner`, `insights-to-plan`, `handoff`, `using-git-worktrees`.

### `check_compliance(skill_name: str, response_summary: str)`

Checks whether a model response complies with a skill's expected output pattern. Returns a checklist with pass/fail for each expected element. All 14 skills have compliance registry entries.

## Available Skills (14)

| Skill | File | Purpose |
|-------|------|---------|
| `systematic-debugging` | `skills/systematic-debugging.md` | Structured debugging: reproduce, hypothesize, verify |
| `brainstorming` | `skills/brainstorming.md` | Refine ideas into validated design docs |
| `writing-plans` | `skills/writing-plans.md` | Design docs into TDD implementation plans |
| `plan-ticket` | `skills/plan-ticket.md` | Plans into YAML ticket contract templates |
| `create-ticket` | `skills/create-ticket.md` | YAML / contract → Linear issue via MCP |
| `consume-ticket` | `skills/consume-ticket.md` | Linear intake **or** mark done (`save_comment` + `save_issue`) |
| `pr-review` | `skills/pr-review.md` | Severity-classified PR review with merge readiness verdict |
| `pr-polish` | `skills/pr-polish.md` | Three-phase PR refinement to merge-ready state |
| `hostile-reviewer` | `skills/hostile-reviewer.md` | Adversarial code review with iterative convergence |
| `defense-in-depth` | `skills/defense-in-depth.md` | Four-layer validation for data-flow bugs |
| `merge-planner` | `skills/merge-planner.md` | PR classification and priority-ordered merge planning |
| `insights-to-plan` | `skills/insights-to-plan.md` | Convert analysis findings into prioritized action plans |
| `handoff` | `skills/handoff.md` | Session continuity through structured context capture |
| `using-git-worktrees` | `skills/using-git-worktrees.md` | Isolated workspace creation with safety verification |

## End-to-End Flow in Cursor

A typical session using all three MCP tools:

0. **Optional — Linear bookends:** **`@17-consume-ticket`** at start → `get_issue` → intake → `@11` / `@13`. When work is done, **`@17-consume-ticket`** again → user confirms AC → `save_comment` + `save_issue` (Done) → re-fetch to verify.

1. **User invokes `@10-brainstorming` with an idea.**
   - Rule calls `get_agent_context("brainstorming")` for routing context.
   - Rule calls `invoke_skill("brainstorming")` for the full methodology.
   - Collaborative dialogue refines the idea into a design doc.
   - Rule calls `check_compliance("brainstorming", summary)` to verify output quality.
   - Design saved to `docs/plans/YYYY-MM-DD-<topic>-design.md`.

2. **User invokes `@11-writing-plans` with the design doc path.**
   - Rule calls `get_agent_context("planning")` for routing context.
   - Design is broken into bite-sized TDD tasks with adversarial review.
   - Rule calls `check_compliance("writing-plans", summary)` to verify.
   - Plan saved to `docs/plans/YYYY-MM-DD-<feature>.md`.

3. **User invokes `@12-plan-ticket` with the plan path.**
   - Rule calls `get_agent_context("ticketing")` for routing context.
   - Deterministic repo detection runs. YAML ticket template generated.
   - Rule calls `check_compliance("plan-ticket", summary)` to verify.

4. **Optional — user invokes `@16-create-ticket`** with the YAML (or `invoke_skill("create-ticket")`).
   - Follow the skill: read Linear MCP tool schemas, then `save_issue` (or equivalent) to create the issue.
   - Rule calls `check_compliance("create-ticket", summary)` after creation or dry-run.

**Other external systems (Kafka, full ONEX runtime, etc.):** not in this repo’s scope — see `docs/ARCHITECTURE.md`. **Linear** is supported when Cursor’s Linear MCP is enabled (`16-create-ticket` / `create-ticket`, and `17-consume-ticket` / `consume-ticket`).

## Hooks

Cursor hooks are deterministic Python scripts that fire on editor lifecycle events. They are **not** interpreted by the LLM — they run as subprocesses before or after specific actions. No pip dependencies required (stdlib only).

### Configuration

`.cursor/hooks.json` controls which scripts run and when. To disable all hooks, rename it to `.cursor/hooks.json.disabled`.

### Active Hooks

**`beforeSubmitPrompt` → `on_prompt.py`** — Classifies each prompt against the 17 agent configs in `.cursor/agents/` using three-strategy scoring: exact substring match (0.95), fuzzy `SequenceMatcher` with length-aware thresholds, and keyword overlap (0.55–0.85). `HARD_FLOOR = 0.55` discards weak matches. Emits `{"systemMessage": "<!-- OmniCursor Agent: <name> (confidence: <score>) -->"}` with the selected agent and any learned patterns from `~/.omnicursor/learned_patterns.json`. Falls back to `polymorphic-agent` with score 0.0 when no agent matches. Whether Cursor actually consumes the `systemMessage` output from `beforeSubmitPrompt` hooks is a platform uncertainty — the hook always emits it regardless.

**`beforeShellExecution` → `on_shell.py`** — Guards against dangerous shell commands using a two-tier regex system. 9 hard-blocked patterns (e.g., `rm -rf /`, `--no-verify`, fork bombs, `base64 --decode | sh`) are denied outright. 11 risky patterns (e.g., `git push --force`, `DROP TABLE`, `curl | sh`, `eval`) are allowed with a warning injected into the agent context.

**`afterFileEdit` → `on_edit.py`** — Logs every file edit with language detection and edit count. For Python files, runs `ruff check` (diagnostic only, never `--fix`) and logs any issues.

**`stop` → `on_stop.py`** — Aggregates all events for the ending conversation: prompt classifications, unique files edited, shell command decisions, and languages used. Classifies the session outcome using a 4-gate decision tree (failed → success → abandoned → unknown). Writes a session summary to `~/.omnicursor/sessions/<conversation_id>.json`.

### Supporting Modules

- **`_common.py`** — Shared path constants (`HOOKS_DIR`, `REPO_ROOT`, `AGENTS_DIR`, `OMNICURSOR_DIR`, `EVENTS_LOG`, `SESSIONS_DIR`, `LEARNED_PATTERNS_FILE`), stdin/stdout JSON helpers, event logging, agent config loading.
- **`pattern_loader.py`** — Thread-safe in-memory `PatternCache` singleton. Warms from `~/.omnicursor/learned_patterns.json` on first use. Provides `get()` by domain, `is_warm()`, `is_stale()` (10-minute TTL). Used by `on_prompt.py` to inject learned patterns into the `systemMessage`.

### Verifying Hooks Work

```bash
# Smoke test on_prompt.py (should show agent + confidence)
echo '{"prompt": "help me debug this error"}' | python3 .cursor/hooks/on_prompt.py

# Smoke test on_shell.py (should deny)
echo '{"command": "rm -rf /"}' | python3 .cursor/hooks/on_shell.py

# Smoke test on_stop.py (session outcome)
echo '{"conversation_id": "test-123", "status": "completed"}' | python3 .cursor/hooks/on_stop.py
```

- **Event log**: `cat ~/.omnicursor/events.jsonl` — one JSON line per event
- **Session summaries**: `ls ~/.omnicursor/sessions/` — one file per completed conversation

### Requirements

- Python 3.10+ (same as the MCP server)
- `ruff` (optional) — if installed, `on_edit.py` runs diagnostic linting on Python files

## Notes

- [`docs/dev/HOW_TO_RUN_IN_CURSOR.md`](./dev/HOW_TO_RUN_IN_CURSOR.md) is preserved as the original starter-kit walkthrough.
- [`docs/ARCHITECTURE.md`](./ARCHITECTURE.md) remains the bucket and adapter contract reference.
