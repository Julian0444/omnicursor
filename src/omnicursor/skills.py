"""Local skill loading for OmniCursor."""

from __future__ import annotations

from pathlib import Path
from typing import List

from .db import REPO_ROOT, SKILLS_DIR
from .schemas import SkillDocument


class SkillRepository:
    """Load Markdown skills from the repository-local skills directory."""

    def __init__(self, skills_dir: Path = SKILLS_DIR) -> None:
        self.skills_dir = skills_dir

    def available_skills(self) -> List[str]:
        return sorted(
            path.stem
            for path in self.skills_dir.glob("*.md")
            if path.stem.lower() != "readme"
        )

    def resolve_path(self, skill_name: str) -> Path:
        filename = skill_name if skill_name.endswith(".md") else f"{skill_name}.md"
        return self.skills_dir / filename

    def load_skill(self, skill_name: str) -> SkillDocument:
        path = self.resolve_path(skill_name)
        if not path.exists():
            available = ", ".join(self.available_skills()) or "(none)"
            raise FileNotFoundError(
                f"Skill '{skill_name}' was not found in {self.skills_dir}. "
                f"Available skills: {available}"
            )

        return SkillDocument(
            skill_name=path.stem,
            path=str(path.relative_to(REPO_ROOT)),
            content=path.read_text(encoding="utf-8"),
        )

