"""Compliance checking for OmniCursor skill outputs."""

from __future__ import annotations

from typing import Dict, List, Tuple

from .schemas import ComplianceResult


# Each skill maps to a list of (check_name, keywords) tuples.
# A check passes if ANY of its keywords appear in the response summary.
COMPLIANCE_REGISTRY: Dict[str, List[Tuple[str, List[str]]]] = {
    "systematic-debugging": [
        ("states_problem_clearly", [
            "symptom", "error", "failure", "bug", "issue", "problem",
            "traceback", "exception", "regression",
        ]),
        ("provides_hypothesis", [
            "hypothesis", "hypotheses", "cause", "theory", "suspect",
            "likely", "root cause", "because",
        ]),
        ("suggests_minimal_fix", [
            "fix", "patch", "change", "update", "modify", "resolve",
            "smallest", "minimal",
        ]),
        ("includes_verification_step", [
            "verify", "verification", "test", "confirm", "run",
            "check", "assert", "validate", "reproduce",
        ]),
    ],
    "brainstorming": [
        ("asks_clarifying_questions", [
            "question", "?", "which", "what", "how", "where", "why",
            "option", "choice", "prefer",
        ]),
        ("presents_multiple_approaches", [
            "option a", "option b", "approach", "alternative",
            "trade-off", "tradeoff", "trade off", "pros", "cons",
            "vs", "versus",
        ]),
        ("provides_recommendation", [
            "recommend", "recommendation", "suggest", "preferred",
            "best", "chosen", "selected",
        ]),
        ("includes_design_sections", [
            "architecture", "component", "data flow", "error handling",
            "testing", "design", "structure",
        ]),
        ("references_output_path", [
            "docs/plans/", "design.md", "handoff", "next step",
        ]),
    ],
    "writing-plans": [
        ("has_plan_header", [
            "goal", "architecture", "tech stack", "implementation plan",
        ]),
        ("has_exact_file_paths", [
            ".py", ".ts", ".js", ".yaml", ".yml", ".md",
            "src/", "tests/", "create:", "modify:",
        ]),
        ("follows_tdd_order", [
            "failing test", "test first", "red", "green", "tdd",
            "write test", "run test", "confirm fail", "confirm pass",
        ]),
        ("has_bite_sized_steps", [
            "step 1", "step 2", "step 3", "phase",
            "commit", "git add", "git commit",
        ]),
        ("includes_adversarial_review", [
            "adversarial", "r1", "r2", "review", "count integrity",
            "acceptance criteria",
        ]),
    ],
    "plan-ticket": [
        ("detects_repo", [
            "omniclaude", "omnibase_core", "omnibase_infra", "omnidash",
            "omniintelligence", "omnimemory", "omninode_infra", "repo",
        ]),
        ("outputs_yaml_template", [
            "yaml", "title:", "repo:", "requirements:", "verification:",
            "template", "contract",
        ]),
        ("has_requirements_section", [
            "requirement", "r1", "statement", "rationale", "acceptance",
        ]),
        ("has_verification_section", [
            "verification", "pytest", "lint", "ruff", "mypy",
            "unit_test", "unit test", "blocking",
        ]),
        ("creates_linear_ticket", [
            "tracker.create_issue", "linear", "ticket", "created", "url",
        ]),
    ],
    "pr-review": [
        ("classifies_by_severity", [
            "critical", "major", "minor", "nit", "severity", "priority",
        ]),
        ("assesses_merge_readiness", [
            "merge", "ready", "not ready", "blocking", "verdict",
        ]),
        ("reviews_changed_files", [
            "diff", "changed", "modified", "file", "review",
        ]),
        ("provides_actionable_findings", [
            "fix", "suggest", "should", "must", "change", "update",
        ]),
    ],
    "pr-polish": [
        ("resolves_conflicts", [
            "conflict", "merge", "resolve", "unmerged", "rebase",
        ]),
        ("addresses_review_comments", [
            "review", "comment", "thread", "feedback", "reply",
        ]),
        ("iterates_to_convergence", [
            "iteration", "pass", "consecutive", "converge", "clean",
        ]),
        ("reports_phase_status", [
            "phase", "status", "ready", "push", "summary",
        ]),
    ],
    "hostile-reviewer": [
        ("uses_adversarial_stance", [
            "adversarial", "skeptical", "assume", "hidden", "defect",
        ]),
        ("classifies_findings", [
            "critical", "major", "minor", "nit", "severity",
        ]),
        ("provides_evidence", [
            "file", "evidence", "impact", "fix", "what to change",
        ]),
        ("iterates_to_convergence", [
            "convergence", "consecutive", "clean pass", "iterate", "pass",
        ]),
        ("states_verdict", [
            "verdict", "clean", "risks_noted", "blocking", "stable",
        ]),
    ],
    "defense-in-depth": [
        ("traces_data_flow", [
            "data flow", "trace", "origin", "entry", "failure",
        ]),
        ("validates_at_entry", [
            "entry", "boundary", "api", "reject", "invalid",
        ]),
        ("validates_at_business_logic", [
            "business logic", "semantic", "context", "operation",
        ]),
        ("adds_environment_guards", [
            "environment", "guard", "test", "temp", "production",
        ]),
        ("tests_each_layer", [
            "test", "bypass", "independently", "verify", "layer",
        ]),
    ],
    "merge-planner": [
        ("classifies_pr_type", [
            "accelerator", "normal", "blocked", "classify", "type",
        ]),
        ("scores_priority", [
            "priority", "score", "dimension", "weight", "rank",
        ]),
        ("determines_merge_order", [
            "order", "merge", "queue", "sequence", "first",
        ]),
        ("checks_conflicts", [
            "conflict", "rebase", "base branch", "clean", "target",
        ]),
    ],
    "insights-to-plan": [
        ("categorizes_insights", [
            "insight", "finding", "observation", "friction", "category",
        ]),
        ("assigns_priority_bands", [
            "p0", "p1", "p2", "p3", "priority", "band",
        ]),
        ("produces_task_blocks", [
            "task", "action", "what to do", "plan", "step",
        ]),
        ("includes_acceptance_criteria", [
            "acceptance", "criteria", "done", "outcome", "verify",
        ]),
    ],
    "handoff": [
        ("captures_session_context", [
            "branch", "commit", "file", "session", "context",
        ]),
        ("summarizes_progress", [
            "summary", "accomplished", "progress", "completed", "done",
        ]),
        ("documents_remaining_work", [
            "remaining", "todo", "next", "task", "continue",
        ]),
        ("notes_blockers", [
            "blocker", "warning", "failing", "blocked", "issue",
        ]),
    ],
    "using-git-worktrees": [
        ("selects_directory", [
            "directory", "worktrees", "location", "path", "config",
        ]),
        ("verifies_gitignore", [
            "gitignore", "ignore", "tracked", "exclude", "verify",
        ]),
        ("creates_worktree", [
            "worktree", "branch", "create", "add", "isolat",
        ]),
        ("runs_baseline_tests", [
            "test", "baseline", "passing", "clean", "ready",
        ]),
    ],
    "recap": [
        ("states_outcome", ["outcome", "success", "failed", "abandoned", "unknown"]),
        ("lists_files_edited", ["files edited", "file edited"]),
        ("suggests_next_steps", ["next step", "suggested", "suggest"]),
    ],
    "plan-review": [
        ("checks_count_integrity", ["count", "task", "numeric", "found", "prose"]),
        ("checks_acceptance_criteria", ["acceptance", "criteria", "testable", "vague"]),
        ("states_verdict", ["verdict", "pass", "fail", "critical", "major"]),
    ],
    "plan-to-tickets": [
        ("parses_task_sections", ["task", "## task", "heading", "section", "found"]),
        ("creates_epic", ["epic", "parent epic"]),
        ("returns_ticket_ids", ["ticket", "linear", "created", "OMN-", "id"]),
    ],
    "execute-plan": [
        ("calls_plan_review", ["plan-review", "review", "r1", "r2", "verdict"]),
        ("calls_plan_to_tickets", ["plan-to-tickets", "ticket", "linear", "epic", "OMN-"]),
        ("reports_summary", ["passed", "blocked", "skipped", "summary"]),
    ],
}


def check_compliance(skill_name: str, response_summary: str) -> ComplianceResult:
    """Check a response summary against the compliance registry for a skill."""

    registry_entry = COMPLIANCE_REGISTRY.get(skill_name)

    if registry_entry is None:
        return ComplianceResult(
            skill_name=skill_name,
            checks={},
            compliant=False,
            missing=[f"no_registry_entry_for_{skill_name}"],
        )

    summary_lower = response_summary.lower()
    checks: Dict[str, bool] = {}
    missing: List[str] = []

    for check_name, keywords in registry_entry:
        passed = any(kw.lower() in summary_lower for kw in keywords)
        checks[check_name] = passed
        if not passed:
            missing.append(check_name)

    return ComplianceResult(
        skill_name=skill_name,
        checks=checks,
        compliant=len(missing) == 0,
        missing=missing,
    )
