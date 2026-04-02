# OmniCursor

Cursor-native adaptation of OmniClaude — combining rules, hooks, and tools into a deterministic AI workflow.

## Architecture

OmniCursor has three complementary layers:

1. **Cursor Rules** (7 `.mdc` files in `.cursor/rules/`) — behavior surface for routing and interaction; always-on + keyword-activated
2. **Cursor Hooks** (`.cursor/hooks/`) — 4 hook entrypoints registered in `.cursor/hooks.json`, plus 2 supporting modules (`_common.py`, `pattern_loader.py`). Deterministic, stdlib only, no LLM
3. **MCP Tools** (3 tools in `src/omnicursor/server.py`) — FastMCP backend for agent routing, skill invocation, and compliance validation

## Quick Start

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
omnicursor-server
```

See [`docs/QUICKSTART.md`](./docs/QUICKSTART.md) for full setup instructions.

## Hooks

Deterministic Python scripts that run on Cursor lifecycle events. Configured in `.cursor/hooks.json`.

| Hook | Script | What it does |
|------|--------|--------------|
| `beforeSubmitPrompt` | `on_prompt.py` | Three-strategy agent scoring (exact/fuzzy/keyword), emits `{"systemMessage": ...}` with agent + confidence + learned patterns |
| `beforeShellExecution` | `on_shell.py` | Two-tier command guard: 9 HARD_BLOCK patterns (deny), 11 SOFT_WARN patterns (allow + warning) |
| `afterFileEdit` | `on_edit.py` | Logs edits, runs diagnostic `ruff check` on Python files |
| `stop` | `on_stop.py` | Aggregates session events, classifies outcome (failed/success/abandoned/unknown) via 4-gate decision tree |

Supporting modules: `_common.py` (shared paths and helpers), `pattern_loader.py` (thread-safe in-memory pattern cache).

All hooks use stdlib only (no pip dependencies).

## MCP Tools

| Tool | Purpose |
|------|---------|
| `get_agent_context(category)` | Returns routing context for a rule-selected category |
| `invoke_skill(skill_name)` | Loads a Markdown skill from the `skills/` directory |
| `check_compliance(skill_name, response_summary)` | Validates model output against a skill's expected pattern |

## Agent Configs

16 JSON configs in [`.cursor/agents/`](./.cursor/agents/) define activation patterns for prompt-based agent routing. Each config specifies `explicit_triggers`, `context_triggers`, and `activation_keywords` used by both hooks (`on_prompt.py`) and MCP (`agents.py`) with identical three-strategy scoring:

1. Exact substring match → 0.95 confidence
2. Fuzzy `SequenceMatcher` with length-aware thresholds
3. Keyword overlap → scaled 0.55–0.85

`HARD_FLOOR = 0.55` — candidates below this are discarded.

## Skills

13 Markdown methodology skills in [`skills/`](./skills/):

| Skill | Purpose |
|-------|---------|
| `systematic-debugging` | Reproduce, hypothesize, verify, fix |
| `brainstorming` | Refine ideas into design docs through collaborative dialogue |
| `writing-plans` | Convert designs into TDD implementation plans |
| `plan-ticket` | Generate YAML ticket contract templates with repo detection |
| `adapter-stub` | Bucket 3 dry-run stubs with fail-soft behavior |
| `pr-review` | Severity-classified PR review with merge readiness verdict |
| `pr-polish` | Three-phase PR refinement to merge-ready state |
| `hostile-reviewer` | Adversarial code review with iterative convergence |
| `defense-in-depth` | Four-layer validation for data-flow bugs |
| `merge-planner` | PR classification and priority-ordered merge planning |
| `insights-to-plan` | Convert analysis findings into prioritized action plans |
| `handoff` | Session continuity through structured context capture |
| `using-git-worktrees` | Isolated workspace creation with safety verification |

Each skill has a corresponding compliance registry entry in `src/omnicursor/compliance.py` with 3–5 keyword-based checks.

## Repository Layout

```text
OmniCursor/
├── .cursor/
│   ├── rules/              # 7 Cursor rules (.mdc)
│   ├── hooks/              # 4 hook entrypoints + _common.py + pattern_loader.py
│   ├── hooks.json          # Hook configuration
│   └── agents/             # 16 JSON agent configs
├── docs/                   # Architecture, quickstart, guides
├── skills/                 # 13 Markdown skill files
├── src/omnicursor/         # Python MCP backend
├── tests/                  # Unit tests (122 tests)
├── omniclaude-main/        # Read-only OmniClaude reference
├── pyproject.toml          # Package config
└── CLAUDE.md               # Repo conventions and architecture overview
```

## Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v              # 122 tests
ruff check src/ tests/ .cursor/hooks/
```

## Documentation

- [`CLAUDE.md`](./CLAUDE.md) — Repo conventions, architecture overview, source-of-truth hierarchy
- [`docs/QUICKSTART.md`](./docs/QUICKSTART.md) — Setup, MCP tools, hooks, and end-to-end flow
- [`docs/HANDOFF.md`](./docs/HANDOFF.md) — Current implementation state and remaining work
- [`docs/OMNICURSOR_IMPLEMENTATION_BRIEF.md`](./docs/OMNICURSOR_IMPLEMENTATION_BRIEF.md) — Implementation decisions and copy map from OmniClaude
- [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) — Starter-pack bucket model and frozen adapter contract
- [`docs/DEVELOPER.md`](./docs/DEVELOPER.md) — Module mapping and contributor orientation
- [`docs/STUDENT_GUIDE.md`](./docs/STUDENT_GUIDE.md) — Original capstone project roadmap (historical)
