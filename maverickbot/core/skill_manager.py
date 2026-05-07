"""Skill manager with /skillname trigger support."""
import os
import importlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from loguru import logger
import yaml


SKILLS_DIR = Path(__file__).parent.parent / "skills"
AVAILABLE_DIR = SKILLS_DIR / "available"
CUSTOM_DIR = SKILLS_DIR / "custom"


@dataclass
class SkillStep:
    """A single step in a skill workflow."""
    action: str
    use_tool: Optional[str] = None
    prompt: Optional[str] = None
    with_config: Optional[Dict[str, Any]] = None


@dataclass
class Skill:
    """Skill definition."""
    name: str
    version: str
    description: str
    tools_required: List[str]
    system_prompt: str
    workflow_type: str  # "yaml" or "python"
    path: Path
    workflow_path: Optional[Path] = None
    workflow_steps: Optional[List[SkillStep]] = None
    config: Dict[str, Any] = None

    def __post_init__(self):
        if self.config is None:
            self.config = {}


class SkillManager:
    """Manages skills with /skillname activation."""

    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._active_skills: List[str] = []
        self._loaded = False

    def discover_all(self) -> None:
        """Discover all skills from available/ and custom/ directories."""
        if self._loaded:
            return

        self._discover_from_dir(AVAILABLE_DIR)
        self._discover_from_dir(CUSTOM_DIR)
        self._loaded = True
        logger.info(f"Discovered {len(self._skills)} skills")

    def _discover_from_dir(self, skills_dir: Path) -> None:
        """Discover skills from a directory."""
        if not skills_dir.exists():
            return

        for skill_path in skills_dir.iterdir():
            if not skill_path.is_dir() or skill_path.name.startswith("_"):
                continue

            skill = self._load_skill(skill_path)
            if skill:
                self._skills[skill.name] = skill
                logger.debug(f"Loaded skill: {skill.name}")

    def _load_skill(self, skill_path: Path) -> Optional[Skill]:
        """Load a skill from its directory."""
        skill_yaml_path = skill_path / "skill.yaml"
        if not skill_yaml_path.exists():
            return None

        try:
            with open(skill_yaml_path, "r") as f:
                data = yaml.safe_load(f)

            skill_def = data.get("skill", data)

            workflow_type = "yaml"
            workflow_path = None
            workflow_steps = None

            workflow_def = skill_def.get("workflow", "")
            if isinstance(workflow_def, str) and workflow_def == "custom":
                workflow_type = "python"
                workflow_path = skill_path / "workflow.py"
            elif isinstance(workflow_def, list):
                workflow_steps = []
                for step in workflow_def:
                    if isinstance(step, dict):
                        workflow_steps.append(SkillStep(
                            action=step.get("action", ""),
                            use_tool=step.get("use_tool"),
                            prompt=step.get("prompt"),
                            with_config=step.get("with"),
                        ))

            return Skill(
                name=skill_def.get("name", skill_path.name),
                version=skill_def.get("version", "1.0.0"),
                description=skill_def.get("description", ""),
                tools_required=skill_def.get("tools_required", []),
                system_prompt=skill_def.get("system_prompt", ""),
                workflow_type=workflow_type,
                workflow_path=workflow_path,
                workflow_steps=workflow_steps,
                config=skill_def.get("config", {}),
                path=skill_path,
            )
        except Exception as e:
            logger.warning(f"Failed to load skill from {skill_path.name}: {e}")
            return None

    def get_skills(self) -> Dict[str, Skill]:
        """Get all discovered skills."""
        if not self._loaded:
            self.discover_all()
        return self._skills

    def get_skill(self, name: str) -> Optional[Skill]:
        """Get a specific skill by name."""
        skills = self.get_skills()
        return skills.get(name)

    def activate_skill(self, name: str) -> bool:
        """Activate a skill by name (triggered via /skillname)."""
        skill = self.get_skill(name)
        if not skill:
            logger.warning(f"Skill not found: {name}")
            return False

        if name not in self._active_skills:
            self._active_skills.append(name)
            logger.info(f"Activated skill: {name}")
        return True

    def deactivate_skill(self, name: str) -> bool:
        """Deactivate a skill."""
        if name in self._active_skills:
            self._active_skills.remove(name)
            logger.info(f"Deactivated skill: {name}")
            return True
        return False

    def get_active_skills(self) -> List[str]:
        """Get list of currently active skills."""
        return self._active_skills.copy()

    def get_active_skill_configs(self) -> List[Dict[str, Any]]:
        """Get configurations of all active skills."""
        configs = []
        for name in self._active_skills:
            skill = self.get_skill(name)
            if skill:
                configs.append({
                    "name": skill.name,
                    "system_prompt": skill.system_prompt,
                    "tools_required": skill.tools_required,
                    "config": skill.config,
                    "workflow_type": skill.workflow_type,
                    "workflow_steps": skill.workflow_steps,
                    "workflow_path": skill.workflow_path,
                })
        return configs

    def list_skills(self) -> List[Dict[str, str]]:
        """List all skills with their metadata."""
        skills = self.get_skills()
        return [
            {
                "name": name,
                "description": skill.description,
                "version": skill.version,
                "tools": ", ".join(skill.tools_required),
            }
            for name, skill in skills.items()
        ]

    def reload(self) -> None:
        """Reload all skills."""
        self._skills.clear()
        self._active_skills.clear()
        self._loaded = False
        self.discover_all()
        logger.info("Skills reloaded")