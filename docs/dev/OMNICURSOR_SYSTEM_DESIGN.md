# OmniCursor — systems design

High-level architecture diagrams for OmniCursor and its optional relationship to the broader OmniNode stack (OmniClaude-style runtimes). Mermaid renders on GitHub and many other viewers.

---

## 1. OmniCursor — runtime layers (inside the IDE)

```mermaid
flowchart TB
  subgraph IDE["Cursor IDE"]
    subgraph L1["Layer 1 — Rules"]
      R[".cursor/rules/*.mdc\n(always-on + keyword)"]
    end

    subgraph L2["Layer 2 — Hooks"]
      HJ[".cursor/hooks.json"]
      HP["on_prompt.py\nbeforeSubmitPrompt"]
      HS["on_shell.py\nbeforeShellExecution"]
      HE["on_edit.py\nafterFileEdit"]
      HO["on_stop.py\nstop"]
      HJ --> HP & HS & HE & HO
    end

    subgraph Skills["Methodology"]
      MD["skills/*.md\n(read by model)"]
    end

    subgraph User["Developer"]
      U["Prompts, edits, terminal"]
    end

    U --> R
    U --> HJ
    R --> MD
  end

  subgraph Local["Local persistence (optional)"]
    E["~/.omnicursor/events.jsonl"]
    P["~/.omnicursor/learned_patterns.json"]
    S["~/.omnicursor/sessions/*"]
  end

  HP & HS & HE & HO --> E
  HP --> P
  HO --> S

  subgraph Lib["Repo: Python library (not in hook process)"]
    A["agents.py\nget_agent_context"]
    SK["skills.py\nSkillRepository"]
    C["compliance.py"]
    NC["node_contracts.py\n+ nodes/*/contract.yaml"]
  end

  Lib --> CI["pytest / CI / scripts"]
```

**Constraints:** Hook scripts under `.cursor/hooks/` use **stdlib only** and **must not** import `omnicursor`. The library under `src/omnicursor/` is for **tests**, **CI**, **optional CLIs**, or **subprocess** helpers invoked from outside the hook interpreter.

---

## 2. OmniCursor in the broader OmniNode ecosystem

Optional ways to align with OmniClaude / ONEX without running the full kernel inside Cursor:

```mermaid
flowchart LR
  subgraph CursorHost["OmniCursor — Cursor host"]
    Rules["Rules"]
    Hooks["Hooks"]
    Skills["skills/*.md"]
    PyLib["src/omnicursor\n(library)"]
    Rules --> Skills
    Hooks --> Skills
  end

  subgraph Integrate["Integration options (by need)"]
    HTTP["HTTP ONEX / skill API\n(see docs/ARCHITECTURE.md)"]
    SUB["Subprocess / CLI\nmay import omnibase_*"]
    KAFKA["Optional event publisher\n(Kafka, sidecar / CI)"]
  end

  subgraph ONEX["OmniNode / ONEX stack (e.g. OmniClaude)"]
    OC["omniclaude\nnodes + plugin"]
    CORE["omnibase-core / spi"]
    INFRA["omnibase-infra\nruntime, contracts, bus"]
    INTEL["omninode-intelligence"]
    BUS[("Kafka / platform events")]
    OC --> CORE & INFRA & INTEL
    INFRA --> BUS
    OC --> BUS
  end

  PyLib -.-> SUB
  SUB -.-> CORE
  Skills -.-> HTTP
  HTTP -.-> INFRA
  PyLib -.-> KAFKA
  KAFKA -.-> BUS

  style CursorHost fill:#f5f5f5
  style ONEX fill:#e8f4fc
```

Solid arrows: primary OmniCursor flows. Dotted arrows: **optional** integration paths.

---

## Related docs

- [`ADR-hook-first-architecture.md`](./ADR-hook-first-architecture.md) — rules vs hooks vs library
- [`OMNICURSOR_NODE_CONTRACTS.md`](./OMNICURSOR_NODE_CONTRACTS.md) — `contract.yaml` layout
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — starter-pack buckets and frozen HTTP adapter
- [`../QUICKSTART.md`](../QUICKSTART.md) — setup and end-to-end usage
