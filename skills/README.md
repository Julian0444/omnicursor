# Skills have moved

Skills are mirrored under `.cursor/skills/onex-<stem>/SKILL.md` (Cursor slash-picker uses each `onex-<stem>` subdirectory name).
Canonical skill ids are **`onex-<name>`** (same as the directory name `<name>`).

Each skill is a directory containing a `SKILL.md` with YAML frontmatter
(`name:`, `description:`) followed by the skill instructions. Cursor
discovers them natively in its skill picker.

See `.cursor-plugin/plugin.json` (official manifest) and `cursor-plugin.json` (install/surfaces companion).
