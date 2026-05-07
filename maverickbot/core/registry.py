"""Central registry for tools, providers, and skills."""
from typing import Dict, List, Any, Optional
from loguru import logger

from .plugin_loader import PluginLoader
from .skill_manager import SkillManager


class Registry:
    """Central registry combining plugin loader and skill manager."""

    def __init__(self):
        self.plugin_loader = PluginLoader()
        self.skill_manager = SkillManager()
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the registry by discovering all plugins and skills."""
        if self._initialized:
            return

        logger.info("Initializing registry...")
        self.plugin_loader.discover_all()
        self.skill_manager.discover_all()
        self._initialized = True
        logger.info("Registry initialized")

    def reload(self) -> None:
        """Reload all plugins and skills."""
        self.plugin_loader.reload()
        self.skill_manager.reload()
        logger.info("Registry reloaded")

    def list_tools(self) -> List[Dict[str, str]]:
        """List all available tools."""
        return self.plugin_loader.list_tools()

    def list_providers(self) -> List[Dict[str, str]]:
        """List all available providers."""
        return self.plugin_loader.list_providers()

    def list_skills(self) -> List[Dict[str, str]]:
        """List all available skills."""
        return self.skill_manager.list_skills()

    def get_tool(self, name: str) -> Optional[Any]:
        """Get a tool class by name."""
        return self.plugin_loader.get_tool(name)

    def get_provider(self, name: str) -> Optional[type]:
        """Get a provider class by name."""
        return self.plugin_loader.get_provider(name)

    def get_skill(self, name: str) -> Optional[Any]:
        """Get a skill by name."""
        return self.skill_manager.get_skill(name)

    def activate_skill(self, name: str) -> bool:
        """Activate a skill via /skillname command."""
        return self.skill_manager.activate_skill(name)

    def deactivate_skill(self, name: str) -> bool:
        """Deactivate a skill."""
        return self.skill_manager.deactivate_skill(name)

    def get_active_skills(self) -> List[str]:
        """Get list of active skill names."""
        return self.skill_manager.get_active_skills()

    def get_active_skill_configs(self) -> List[Dict[str, Any]]:
        """Get configurations of active skills."""
        return self.skill_manager.get_active_skill_configs()

    def get_all_tools(self) -> Dict[str, Any]:
        """Get all tools."""
        return self.plugin_loader.get_tools()