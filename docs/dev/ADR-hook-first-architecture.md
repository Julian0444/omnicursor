# ADR: Hook-First Architecture (Rules + MCP De-Duplication)

**Status:** Accepted (design direction)  
**Context:** OmniCursor Linear **OMN-37**; related **OMN-12**, **OMN-39**, **OMN-44**  
**Scope:** Documentation only — describes ownership and migration **phases** without requiring immediate code deletion.

---

## Context

OmniCursor has three behavioral layers:

1. **Cursor Rules** (`.cursor/rules/*.mdc`) — instructions the model sees when keywords match; can invoke MCP tools.
2. **Cursor Hooks** (`.cursor/hooks/`) — deterministic, stdlib-only scripts on lifecycle events; see [`CURSOR_VS_CLAUDE_HOOKS.md`](./CURSOR_VS_CLAUDE_HOOKS.md).
3. **MCP** (`src/omnicursor/`) — `get_agent_context`, `invoke_skill`, `check_compliance`.

**Problem statement:** The same **concerns** (routing, compliance, patterns, telemetry) can appear in more than one layer. Without explicit ownership, documentation and behavior drift (e.g. two scoring implementations).

---

## Decision

Adopt a **hook-first** default for ** lifecycle-triggered, deterministic** work that must run without the model choosing to call a tool:

- **Hooks** own: prompt-time classification payload (`systemMessage`), shell gating, edit-time lint signal, stop-time session outcome aggregation, append-only event logging to `~/.omnicursor/events.jsonl`.
- **Rules** own: methodology text, bucket boundaries, keyword activation, and **optional** MCP calls when the model is already in a rule-guided flow.
- **MCP** own: **structured** responses (agent context document, skill body, compliance result) and anything that must be **invoked on demand** by the agent or a rule.

**Non-goal:** Removing MCP or rules in favor of hooks-only automation. Hooks cannot replace skill text or compliance API shape.

---

## Ownership table

| Concern | Primary owner | Secondary / duplicate today | Direction |
|---------|---------------|----------------------------|-----------|
| Prompt → agent scoring | Hook: `on_prompt.py` | MCP: `agents.py` (same algorithms, `HARD_FLOOR = 0.55`) | **Keep dual path**; document drift risk; optional future: generate one module from the other in build step (out of scope for this ADR) |
| Inject learned patterns | Hook + `pattern_loader.py` | MCP: pattern list APIs static in `patterns.py`; future `store_pattern` | Hooks **inject**; MCP **serves** and (later) **persists** new patterns |
| Compliance checking | MCP: `check_compliance` | Rules may remind model to check | **MCP** is authoritative for machine-checkable output |
| Skill content | `skills/*.md` via MCP `invoke_skill` | Rules reference skills | **Skills** remain Markdown; rules point to workflows |
| Dangerous shell commands | Hook: `on_shell.py` | Rules may warn in prose | **Hook** is authoritative for **deny** |
| Post-edit Python quality signal | Hook: `on_edit.py` | Optional CI / local ruff | **Hook** for immediate feedback signal + logging |
| Session outcome taxonomy | Hook: `on_stop.py` | — | **Hook** |
| Bounded research discipline | Rules: `01-codebase-research.mdc` | Future `beforeReadFile` (Phase 3B) | **Rules** until hook exists |

---

## Duplication risks (explicit)

1. **Scoring** in `on_prompt.py` and `agents.py` — must stay aligned manually until a codegen/shared stub strategy is justified.
2. **Routing narrative** in rules vs what hooks emit — mitigate by linking to this ADR and `CURSOR_VS_CLAUDE_HOOKS.md`.
3. **Compliance** reminders in rules vs `check_compliance` — rubric and tests should favor MCP/tool calls for verifiable checks.

---

## Phased migration (documentation and implementation)

| Phase | Focus | Success criterion |
|-------|--------|-------------------|
| **A (current)** | Hooks implement `systemMessage`, patterns, shell guard, ruff-on-edit, stop classification; MCP provides tools; rules preserved | Tests green; hook smoke tests documented |
| **B** | Phase 3B hooks (`beforeMCPExecution`, `beforeReadFile`) if/when available — reduce reliance on pure rule text for “don’t do X before Y” | New hook entries in `hooks.json` + tests |
| **C** | Optional `store_pattern` MCP tool — close HANDOFF demo gap for cross-session learning | Pattern write path + tests |
| **D** | Consolidation pass — trim redundant prose in rules only where hooks/MCP clearly own the behavior | No behavioral regression; rubric evidence updated |

---

## Consequences

- **Positive:** Clear place to add lifecycle automation; easier grading narrative (hooks = observable side effects).
- **Negative:** Two copies of scoring logic; `systemMessage` consumption remains product-dependent.
- **Tests:** Existing suite remains the guardrail; new hook phases add tests alongside `tests/` patterns already used for hooks and agents.

---

## References

- [`CURSOR_VS_CLAUDE_HOOKS.md`](./CURSOR_VS_CLAUDE_HOOKS.md)
- `CLAUDE.md`, [`DEVELOPER.md`](./DEVELOPER.md), [`HANDOFF.md`](./HANDOFF.md)
- `OmniCursor_DoD_Rubric.md`
