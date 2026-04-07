from omnicursor.compliance import check_compliance, COMPLIANCE_REGISTRY


def test_systematic_debugging_fully_compliant() -> None:
    summary = (
        "The symptom was a TypeError exception in the parser. "
        "The hypothesis is that the input validator rejects None values. "
        "The fix changes the validator to handle None. "
        "Verification: run pytest to confirm the test passes."
    )
    result = check_compliance("systematic-debugging", summary)
    assert result.skill_name == "systematic-debugging"
    assert result.compliant is True
    assert result.missing == []
    assert all(result.checks.values())


def test_systematic_debugging_missing_fix() -> None:
    summary = (
        "The symptom was a timeout error. "
        "The root cause is a missing retry in the HTTP client. "
        "Verification: run the test suite to confirm."
    )
    result = check_compliance("systematic-debugging", summary)
    assert result.compliant is False
    assert "suggests_minimal_fix" in result.missing
    assert result.checks["states_problem_clearly"] is True
    assert result.checks["provides_hypothesis"] is True
    assert result.checks["suggests_minimal_fix"] is False
    assert result.checks["includes_verification_step"] is True


def test_brainstorming_fully_compliant() -> None:
    summary = (
        "Which approach do you prefer? Option A uses a REST API, "
        "Option B uses GraphQL. The trade-off is simplicity vs flexibility. "
        "I recommend Option A because it fits the existing architecture. "
        "The design covers component structure and data flow. "
        "Saved to docs/plans/2026-03-28-webhook-design.md."
    )
    result = check_compliance("brainstorming", summary)
    assert result.skill_name == "brainstorming"
    assert result.compliant is True
    assert result.missing == []


def test_brainstorming_missing_approaches() -> None:
    summary = (
        "Here is the design for the webhook feature. "
        "The architecture uses a REST endpoint. "
        "Saved to docs/plans/2026-03-28-webhook-design.md."
    )
    result = check_compliance("brainstorming", summary)
    assert result.compliant is False
    assert "presents_multiple_approaches" in result.missing


def test_unknown_skill_returns_no_registry() -> None:
    result = check_compliance("nonexistent-skill", "some summary")
    assert result.compliant is False
    assert "no_registry_entry_for_nonexistent-skill" in result.missing
    assert result.checks == {}


def test_all_skills_have_registry_entries() -> None:
    expected = {
        "systematic-debugging",
        "brainstorming",
        "writing-plans",
        "plan-ticket",
        "pr-review",
        "pr-polish",
        "hostile-reviewer",
        "defense-in-depth",
        "merge-planner",
        "insights-to-plan",
        "handoff",
        "using-git-worktrees",
    }
    assert set(COMPLIANCE_REGISTRY.keys()) == expected


def test_writing_plans_compliance() -> None:
    summary = (
        "Implementation plan. Goal: add webhook support. "
        "Architecture: REST API with queue. Tech stack: Python, FastAPI. "
        "Phase 1: Step 1: Write the failing test in tests/test_webhook.py. "
        "Step 2: Run test to confirm fail. Step 3: Implement src/webhook.py. "
        "Commit: git add && git commit. "
        "Adversarial review: R1 count integrity checked, R2 acceptance criteria checked."
    )
    result = check_compliance("writing-plans", summary)
    assert result.compliant is True


def test_plan_ticket_compliance() -> None:
    summary = (
        "Detected repo: omniclaude. "
        "Generated YAML template with title: 'Add webhook endpoint'. "
        "Requirements section with R1 statement and acceptance criteria. "
        "Verification: pytest and ruff lint checks. Blocking: true."
    )
    result = check_compliance("plan-ticket", summary)
    assert result.compliant is True
