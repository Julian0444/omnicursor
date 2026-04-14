# `omnicursor` Python package

Library code used by **tests**, **CI**, and optional **local scripting**. IDE behavior comes from **rules**, **hooks**, and reading **`skills/*.md`**.

| Module | Role |
|--------|------|
| [`agents.py`](./agents.py) | Category → `AgentContext` (routing instructions, recommended skill). Mirrors hook scoring in `.cursor/hooks/on_prompt.py` (must stay aligned manually). |
| [`skills.py`](./skills.py) | Load Markdown skills from `skills/` into `SkillDocument`. |
| [`compliance.py`](./compliance.py) | Keyword-based `check_compliance` for rubric-style verification. |
| [`schemas.py`](./schemas.py) | Pydantic models shared by the above. |
| [`node_contracts.py`](./node_contracts.py) | Discover / validate Cursor-native node `contract.yaml` files under `nodes/`. |

**Tests:** `pytest tests/` from the repository root.
