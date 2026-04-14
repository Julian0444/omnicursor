# Markdown skills

Each file is human-readable skill content. The model reads these paths from Cursor rules; `src/omnicursor/skills.py` loads the same files for tests. Names match library arguments (e.g. `brainstorming`, `plan-ticket`).

**Compliance:** `check_compliance` uses `src/omnicursor/compliance.py` — add registry entries when you add skills that need automated checks.

**Buckets:** Skills here are Bucket 1/2 methodology. Bucket 3 (external integration) is described only in [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) — there is no `adapter-stub` skill file in this repo.

**Reference:** [OMNICLAUDE_SKILLS.md](../OMNICLAUDE_SKILLS.md) (read-only comparison to upstream omniclaude skills).
