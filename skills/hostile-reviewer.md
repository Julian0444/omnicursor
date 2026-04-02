# Hostile Reviewer

Use this skill for adversarial code review when you need to find issues that a normal review would miss. The goal is to act as a skeptical, thorough reviewer who assumes nothing is correct until proven otherwise.

## Purpose

Perform a deep adversarial review of code changes or design documents. A single review pass catches roughly 60% of issues — fixes from pass N routinely introduce 2-4 new issues caught in pass N+1. This skill iterates to convergence to eliminate that false-completeness problem.

## Prerequisites

- A PR diff, set of changed files, or a design document to review
- Willingness to iterate (this skill does not rubber-stamp)

## Workflow

1. **Adopt the adversarial stance.**
   Assume every change has a hidden defect. Focus on: invariant gaps, integration boundary failures, missing error handling, race conditions, and untested edge cases. No praise, no qualifiers — findings only.

2. **Review with severity classification.**
   For each finding, assign one severity:
   - **CRITICAL** — Security flaws, data loss, architectural redesign required.
   - **MAJOR** — Performance issues, missing error handling, incomplete tests.
   - **MINOR** — Code quality, documentation gaps, edge cases.
   - **NIT** — Formatting, naming, minor refactoring suggestions.

3. **Report findings with evidence.**
   Each finding must include: file path, what is wrong, why it matters, and what to change (three sentences max per finding). No vague observations — every finding must be actionable.

4. **Iterate to convergence.**
   After findings are addressed, re-review the updated code. A "clean pass" means no findings above NIT severity. Require two consecutive clean passes before declaring the review complete. Cap at 10 passes.

5. **Produce the final verdict.**
   - `clean` — Two consecutive clean passes achieved. Code is stable.
   - `risks_noted` — MAJOR findings exist but are addressable.
   - `blocking_issue` — CRITICAL findings remain. Must fix before merge.

## Expected Output Format

A structured review with:
- Findings grouped by severity (CRITICAL first)
- Each finding: file, issue, impact, fix (three sentences max)
- Iteration summary: pass count, findings per pass, convergence status
- Final verdict

## Quality Checklist

- [ ] Every finding includes file path, issue, and suggested fix
- [ ] Severity levels are used consistently (CRITICAL / MAJOR / MINOR / NIT)
- [ ] No rubber-stamping — at least one full review pass was performed
- [ ] Convergence required two consecutive clean passes (not just one)
- [ ] Final verdict is explicitly stated
