import pytest

from omnicursor.skills import SkillRepository


@pytest.fixture
def repository() -> SkillRepository:
    return SkillRepository()


def test_load_systematic_debugging_skill(repository: SkillRepository) -> None:
    skill = repository.load_skill("systematic-debugging")
    assert skill.skill_name == "systematic-debugging"
    assert skill.path == "skills/systematic-debugging.md"
    assert "Systematic Debugging" in skill.content


def test_load_brainstorming_skill(repository: SkillRepository) -> None:
    skill = repository.load_skill("brainstorming")
    assert skill.skill_name == "brainstorming"
    assert skill.path == "skills/brainstorming.md"
    assert "Brainstorming" in skill.content


def test_load_writing_plans_skill(repository: SkillRepository) -> None:
    skill = repository.load_skill("writing-plans")
    assert skill.skill_name == "writing-plans"
    assert skill.path == "skills/writing-plans.md"
    assert "Writing Plans" in skill.content


def test_load_plan_ticket_skill(repository: SkillRepository) -> None:
    skill = repository.load_skill("plan-ticket")
    assert skill.skill_name == "plan-ticket"
    assert skill.path == "skills/plan-ticket.md"
    assert "Plan Ticket" in skill.content


def test_available_skills_lists_all(repository: SkillRepository) -> None:
    available = repository.available_skills()
    expected = [
        "brainstorming",
        "defense-in-depth",
        "handoff",
        "hostile-reviewer",
        "insights-to-plan",
        "merge-planner",
        "plan-ticket",
        "pr-polish",
        "pr-review",
        "systematic-debugging",
        "using-git-worktrees",
        "writing-plans",
    ]
    assert available == expected


def test_load_nonexistent_skill_raises(repository: SkillRepository) -> None:
    with pytest.raises(FileNotFoundError, match="nonexistent"):
        repository.load_skill("nonexistent")
