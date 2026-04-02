# OmniCursor Handoff Document

**Date**: 2026-04-01
**Purpose**: Enable any developer or AI session to resume implementation without re-reading the entire codebase.

---

## 1. What OmniCursor Is

OmniCursor is a **Cursor-native adaptation of OmniClaude** — a three-layer system that makes an AI coding assistant behave more intelligently without the LLM having to decide to do so:

1. **Cursor Rules** (`.cursor/rules/*.mdc`, 7 files) — always-on and keyword-activated behavioral instructions
2. **Cursor Hooks** (`.cursor/hooks/`) — 4 hook entrypoints registered in `.cursor/hooks.json`, plus 2 supporting modules (`_common.py`, `pattern_loader.py`). Deterministic Python scripts that fire on lifecycle events
3. **MCP Tools** (`src/omnicursor/server.py`, 3 tools) — FastMCP backend for `get_agent_context`, `invoke_skill`, `check_compliance`

The reference implementation is `omniclaude-main/` (read-only). We selectively adapt its patterns, not mirror it.

---

## 2. Source-of-Truth Hierarchy

When documents disagree:

1. Actual current codebase behavior
2. `CLAUDE.md` — repo conventions and architecture overview
3. `docs/OMNICURSOR_IMPLEMENTATION_BRIEF.md` — implementation decisions
4. `omnicursor-team-guidance.md` — Jonah's demo-focused guidance with code examples
5. `omniclaude-main/` — reference library, never a source of mandatory parity

---

## 3. What Has Been Completed

### Tasks 0–4: Core Infrastructure

- **Task 0** — Full codebase analysis and upgrade path identification
- **Task 1** — `on_prompt.py` enrichment-ready routing: `_score_agent()` returns `(score, reason)`, `classify_prompt()` returns `(agent_name, score, reason)` 3-tuple, `main()` emits `{"systemMessage": "<!-- OmniCursor Agent: ... -->"}`
- **Task 2** — JSON-backed learned pattern loading: `PatternCache` class in `pattern_loader.py`, warms from `~/.omnicursor/learned_patterns.json`, injects up to 5 patterns into `systemMessage`
- **Task 3** — Multi-strategy routing in `agents.py`: exact substring (0.95/0.80), fuzzy SequenceMatcher with length-aware thresholds, keyword overlap (0.55–0.85), `HARD_FLOOR = 0.55`, `match_agent_candidates()` returning top-5 candidates
- **Task 4** — Identical three-strategy scoring ported to `on_prompt.py` hook (hooks cannot import from `src/omnicursor/`, so logic is duplicated)

### Task 5: `activation_keywords` in Agent Configs

Added `activation_keywords` (5 keywords each) to all 16 `.cursor/agents/*.json` files. `polymorphic-agent` intentionally has `[]` (fallback agent). This improves Strategy 3 precision over auto-extraction from trigger text.

### Task 6: Session Outcome Classification

Rewrote `on_stop.py` with `derive_session_outcome(status, events)` using a 4-gate decision tree:
- Gate 1 FAILED: status maps to failure OR error markers in event text
- Gate 2 SUCCESS: work was done AND completion markers present
- Gate 3 ABANDONED: no completion markers AND duration < 60s
- Gate 4 UNKNOWN: insufficient signal

Outcome included in both logged stop event and persisted session summary.

### Task 7: Shell Guard Missing Patterns

Added 2 patterns to `on_shell.py`:
- HARD_BLOCK: `base64 --decode | sh` (obfuscated shell execution) — total now 9
- SOFT_WARN: `eval` execution — total now 11

### Task 8A: Port First 4 Methodology Skills

Created `skills/pr-review.md`, `skills/pr-polish.md`, `skills/hostile-reviewer.md`, `skills/defense-in-depth.md`. Added 4 compliance registry entries (4 checks each). Source: `omniclaude-main/plugins/onex/skills/*/SKILL.md`, adapted for Cursor context.

### Task 8B: Port Remaining 4 Methodology Skills

Created `skills/merge-planner.md`, `skills/insights-to-plan.md`, `skills/handoff.md`, `skills/using-git-worktrees.md`. Added 4 compliance registry entries (4 checks each). Source: same, adapted for Cursor.

### Task 9: Final Verification

- 122 tests passing
- `ruff check` clean across `src/`, `tests/`, `.cursor/hooks/`
- All hook smoke tests pass
- MCP server imports cleanly
- 4 unused imports cleaned up (pre-existing lint, not regressions)

---

## 4. Current State of All Files

### Hooks (`.cursor/hooks/`, stdlib only)

| File | Event | Behavior |
|------|-------|----------|
| `on_prompt.py` | `beforeSubmitPrompt` | Three-strategy scoring (exact/fuzzy/keyword), `HARD_FLOOR=0.55`, pattern injection from JSON cache, emits `{"systemMessage": ...}` |
| `pattern_loader.py` | (imported by on_prompt) | Thread-safe `PatternCache` singleton, warms from `~/.omnicursor/learned_patterns.json` |
| `on_shell.py` | `beforeShellExecution` | 9 HARD_BLOCK + 11 SOFT_WARN regex patterns, two-tier deny/warn/allow |
| `on_edit.py` | `afterFileEdit` | Diagnostic `ruff check` on `.py` files, logs to `events.jsonl` |
| `on_stop.py` | `stop` | Aggregates session events, 4-gate outcome classification (failed/success/abandoned/unknown), writes session summary |
| `_common.py` | Shared | Paths (incl. `LEARNED_PATTERNS_FILE`), stdin/stdout, event logging, agent config loading |

### MCP Tools (`src/omnicursor/`)

| Module | Notes |
|--------|-------|
| `server.py` | 3 tools: `get_agent_context`, `invoke_skill`, `check_compliance` |
| `agents.py` | Three-strategy scoring, `HARD_FLOOR=0.55`, `match_agent_candidates()`, backward-compatible `match_agent()`, dynamic JSON loading from `.cursor/agents/*.json` |
| `compliance.py` | Registry for all 13 skills, 3–5 keyword checks each |
| `skills.py` | Auto-discovers `skills/*.md` (13 skills) |
| `schemas.py` | `AgentContext`, `SkillDocument`, `ComplianceResult`, `PatternRecord`, `DatabaseStatus` |
| `db.py` | Repo path constants, `InMemoryDatabase` placeholder |
| `patterns.py` | Lists 4 preserved rules as `PatternRecord` objects (static) |

### Agent Configs (`.cursor/agents/*.json`, 16 files)

Schema: `name`, `description`, `category`, `activation_patterns` (`explicit_triggers`, `context_triggers`, `activation_keywords`), `instructions`, `recommended_skill`.

All 16 configs have `activation_keywords` (5 each, except `polymorphic-agent` which has `[]`).

### Skills (`skills/*.md`, 13 files)

Original (5): `systematic-debugging`, `brainstorming`, `writing-plans`, `plan-ticket`, `adapter-stub`

Ported from OmniClaude (8): `pr-review`, `pr-polish`, `hostile-reviewer`, `defense-in-depth`, `merge-planner`, `insights-to-plan`, `handoff`, `using-git-worktrees`

### Tests

122 tests across 8 test files, all passing. `pytest tests/ -v` runs in ~0.3s.

---

## 5. Demo Success Criteria (from Jonah)

| # | What to Show | Status |
|---|-------------|--------|
| 1 | Prompt auto-routed to correct agent without calling MCP | **Done** — `on_prompt.py` emits agent + confidence + reason via `systemMessage` |
| 2 | File edit auto-linted without user action | **Done** — `on_edit.py` runs diagnostic ruff |
| 3 | Pattern from session A appears in session B | **Partial** — `learned_patterns.json` persists across sessions and is injected via `pattern_loader.py`. Missing: `store_pattern` MCP tool for writing new patterns |
| 4 | Hooks disabled, system degrades to MCP-only | **Done** — MCP server works independently of hooks |

---

## 6. What Remains

| Item | Priority | Description |
|------|----------|-------------|
| `store_pattern` MCP tool | High | Enables writing new patterns from sessions — completes demo criterion 3 |
| Seed `learned_patterns.json` | Medium | Ship a starter JSON file so the demo has pattern data out of the box |
| Valkey integration | Deferred | JSON file persistence works; Valkey is a future performance upgrade |
| `beforeMCPExecution` / `beforeReadFile` hooks | Deferred | Phase 3B — not needed for MVP |

---

## 7. Key Constraints

- `omniclaude-main/` is **read-only** — never modify
- `.cursor/rules/*.mdc` are teaching artifacts — modify with care
- Hooks use **Python stdlib only** (`difflib.SequenceMatcher` is stdlib; `yaml` is not)
- All hooks exit 0 (except `on_shell.py` deny)
- `pyproject.toml` deps stay minimal: `mcp`, `pydantic`
- No Kafka, Qdrant, Slack, PostgreSQL, or Valkey as dependencies

---

## 8. Known Ambiguities

1. **Prompt enrichment may not work.** `on_prompt.py` emits `{"systemMessage": ...}` but Cursor documentation is unclear on whether `beforeSubmitPrompt` output is consumed. The Implementation Brief says: treat this as a capability gate, not a design reset.

2. **Scoring logic is duplicated.** `_score_agent()` exists in both `on_prompt.py` (hooks, stdlib) and `agents.py` (MCP). They are aligned (identical 3-strategy logic) but must stay in sync manually. Hooks cannot import from `src/omnicursor/`.

---

## 9. Running the Project

```bash
# Setup
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Tests (122, ~0.3s)
pytest tests/ -v

# Lint
ruff check src/ tests/ .cursor/hooks/

# Smoke test on_prompt.py
echo '{"prompt": "debug this error in my code"}' | python3 .cursor/hooks/on_prompt.py

# Smoke test on_shell.py
echo '{"command": "rm -rf /"}' | python3 .cursor/hooks/on_shell.py

# Smoke test on_stop.py
echo '{"conversation_id": "test-123", "status": "completed"}' | python3 .cursor/hooks/on_stop.py

# Run MCP server
omnicursor-server
```

---

## 10. How to Build Context for a New Session

Paste this as a preamble:

```
Read these files to build working context:
- CLAUDE.md (conventions and architecture overview)
- docs/HANDOFF.md (current state and remaining tasks)
- docs/OMNICURSOR_IMPLEMENTATION_BRIEF.md (implementation decisions)
- omnicursor-team-guidance.md (Jonah's guidance)
- .cursor/hooks/on_prompt.py, _common.py, pattern_loader.py, on_shell.py, on_stop.py
- src/omnicursor/agents.py, compliance.py, skills.py
```
