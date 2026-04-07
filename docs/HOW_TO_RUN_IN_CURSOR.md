# How to Run in Cursor

> **Historical document.** These are the original starter-pack instructions. The project has since evolved to include hooks, MCP tools, and 12 skills (no `adapter-stub`). For current setup instructions, see [`docs/QUICKSTART.md`](./QUICKSTART.md).

Step-by-step instructions for loading and using the OmniNode Cursor starter pack.

---

## Step 1: Open the Folder

Open `cursor-omninode/` in Cursor:

```
File → Open Folder → select the cursor-omninode/ directory
```

Cursor must open the `cursor-omninode/` folder as the **root** of the workspace — not a parent
directory. Rules in `.cursor/rules/` are only loaded when their containing folder is the workspace root.

---

## Step 2: Confirm Rules Are Loaded

Verify that Cursor loaded all 6 rules:

```
Settings (⌘,) → Rules → should show 6 rules:
  00-omninode-concepts
  01-codebase-research
  10-brainstorming
  11-writing-plans
  12-plan-ticket
```

If rules are missing:
- Confirm you opened `cursor-omninode/` as the root folder (not a parent)
- Check that `.cursor/rules/` contains 6 `.mdc` files: `ls .cursor/rules/`
- Restart Cursor and reopen the folder

---

## Step 3: Trigger a Rule Manually

If a rule does not auto-activate, use the @mention fallback:

1. Open Cursor Composer: `⌘I`
2. Type `@` and the rule name, e.g.:
   ```
   @10-brainstorming I want to add a webhook endpoint to omniclaude
   ```
3. Press Enter — the rule activates and the session begins

**Auto-activation vs @mention:** Both are equally valid. Auto-activation fires when Cursor's
keyword matching detects a match with the rule's `description` frontmatter. @mention is the
reliable fallback when auto-activation doesn't fire.

---

## Step 4: Run a Test Prompt

To test the brainstorming rule:

1. Open `tests/prompts/brainstorming/01-simple-api.md`
2. Copy the prompt text
3. Open Composer (`⌘I`)
4. Paste the prompt (with or without `@10-brainstorming`)
5. Observe the response

Expected behavior:
- Rule announces what files it reads before using them
- First response contains exactly ONE question
- Session eventually produces `docs/plans/YYYY-MM-DD-*-design.md`

---

## Step 5: Troubleshoot If a Rule Doesn't Trigger

If the expected rule doesn't activate:

1. **Check the description field:** Open `.cursor/rules/<rule>.mdc` and verify the `description`
   frontmatter contains keywords matching your prompt.

2. **Use @mention fallback:** Type `@<rule-name>` in Composer to explicitly invoke the rule.
   This always works regardless of keyword matching.

3. **Check alwaysApply:** Rules `00-omninode-concepts` and `01-codebase-research` have
   `alwaysApply: true` — they are always active. If they don't appear active, the folder is
   not opened as the workspace root.

4. **Restart Cursor:** Settings changes and new rule files sometimes require a restart.

---

## Step 6: Outputs

| Output Type | Location | Produced By |
|-------------|----------|------------|
| Design files | `docs/plans/YYYY-MM-DD-*-design.md` | `10-brainstorming` |
| Plan files | `docs/plans/YYYY-MM-DD-*.md` | `11-writing-plans` |
| Ticket templates | stdout (Composer output) | `12-plan-ticket` |
| External / Bucket 3 work | Manual or Cursor MCP outside OmniCursor rules | _(no adapter-stub rule in repo)_ |

---

## Running the Full Chain

To run the complete brainstorm → plan → ticket chain:

1. **Brainstorm:** `@10-brainstorming` + your idea → produces a design file
2. **Plan:** `@11-writing-plans` + "here is the design: [paste path]" → produces a plan file
3. **Ticket:** `@12-plan-ticket` + "here is the plan: [paste path]" → produces a YAML template

Each step references the output of the previous step by file path (not by pasting content).

---

## File Count Verification

To verify you have all 23 expected files:

```bash
find . -type f | grep -v DS_Store | wc -l
```

Expected: 23
