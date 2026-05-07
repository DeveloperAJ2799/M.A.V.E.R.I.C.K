"""Plugin loader with auto-discovery."""
import os
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from loguru import logger
import yaml


PLUGIN_DIR = Path(__file__).parent.parent / "plugins"
TOOLS_DIR = PLUGIN_DIR / "tools"
PROVIDERS_DIR = PLUGIN_DIR / "providers"


@dataclass
class PluginManifest:
    name: str
    version: str
    author: str
    description: str
    entry_point: str
    dependencies: List[str]
    tags: List[str]
    path: Path


class PluginLoader:
    """Auto-discovers and loads plugins from the plugins directory."""

    def __init__(self):
        self._tools: Dict[str, Any] = {}
        self._providers: Dict[str, type] = {}
        self._loaded = False

    def discover_all(self) -> None:
        """Discover all plugins (tools and providers)."""
        if self._loaded:
            return
        
        self._discover_tools()
        self._discover_providers()
        self._loaded = True
        logger.info(f"Discovered {len(self._tools)} tools and {len(self._providers)} providers")

    def _discover_tools(self) -> None:
        """Discover tool plugins from plugins/tools/."""
        if not TOOLS_DIR.exists():
            return

        for plugin_path in TOOLS_DIR.iterdir():
            if not plugin_path.is_dir() or plugin_path.name.startswith("_"):
                continue

            manifest = self._load_manifest(plugin_path)
            if not manifest:
                continue

            tool_class = self._load_tool_class(plugin_path, manifest)
            if tool_class:
                self._tools[manifest.name] = {
                    "class": tool_class,
                    "manifest": manifest,
                    "path": plugin_path,
                }
                logger.debug(f"Loaded tool: {manifest.name}")

    def _discover_providers(self) -> None:
        """Discover provider plugins from plugins/providers/."""
        if not PROVIDERS_DIR.exists():
            return

        for plugin_path in PROVIDERS_DIR.iterdir():
            if not plugin_path.is_dir() or plugin_path.name.startswith("_"):
                continue

            manifest = self._load_manifest(plugin_path)
            if not manifest:
                continue

            provider_class = self._load_provider_class(plugin_path, manifest)
            if provider_class:
                self._providers[manifest.name] = {
                    "class": provider_class,
                    "manifest": manifest,
                    "path": plugin_path,
                }
                logger.debug(f"Loaded provider: {manifest.name}")

    def _load_manifest(self, plugin_path: Path) -> Optional[PluginManifest]:
        """Load manifest.yaml from plugin directory."""
        manifest_path = plugin_path / "manifest.yaml"
        if not manifest_path.exists():
            return None

        try:
            with open(manifest_path, "r") as f:
                data = yaml.safe_load(f)
                return PluginManifest(
                    name=data.get("name", plugin_path.name),
                    version=data.get("version", "1.0.0"),
                    author=data.get("author", "unknown"),
                    description=data.get("description", ""),
                    entry_point=data.get("entry_point", ""),
                    dependencies=data.get("dependencies", []),
                    tags=data.get("tags", []),
                    path=plugin_path,
                )
        except Exception as e:
            logger.warning(f"Failed to load manifest for {plugin_path.name}: {e}")
            return None

    def _load_tool_class(self, plugin_path: Path, manifest: PluginManifest) -> Optional[type]:
        """Load tool class from plugin."""
        if not manifest.entry_point:
            return None

        try:
            init_path = plugin_path / "__init__.py"
            if not init_path.exists():
                return None

            module_name = f"maverickbot.plugins.tools.{manifest.name}"
            spec = importlib.util.spec_from_file_location(module_name, init_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            return getattr(module, manifest.entry_point, None)
        except Exception as e:
            logger.warning(f"Failed to load tool class {manifest.entry_point}: {e}")
            return None

    def _load_provider_class(self, plugin_path: Path, manifest: PluginManifest) -> Optional[type]:
        """Load provider class from plugin."""
        if not manifest.entry_point:
            return None

        try:
            init_path = plugin_path / "__init__.py"
            if not init_path.exists():
                return None

            module_name = f"maverickbot.plugins.providers.{manifest.name}"
            spec = importlib.util.spec_from_file_location(module_name, init_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            return getattr(module, manifest.entry_point, None)
        except Exception as e:
            logger.warning(f"Failed to load provider class {manifest.entry_point}: {e}")
            return None

    def get_tools(self) -> Dict[str, Any]:
        """Get all discovered tools."""
        if not self._loaded:
            self.discover_all()
        return self._tools

    def get_providers(self) -> Dict[str, Any]:
        """Get all discovered providers."""
        if not self._loaded:
            self.discover_all()
        return self._providers

    def get_tool(self, name: str) -> Optional[Any]:
        """Get a specific tool by name."""
        tools = self.get_tools()
        return tools.get(name, {}).get("class")

    def get_provider(self, name: str) -> Optional[type]:
        """Get a specific provider class by name."""
        providers = self.get_providers()
        return providers.get(name, {}).get("class")

    def list_tools(self) -> List[Dict[str, str]]:
        """List all tools with their metadata."""
        tools = self.get_tools()
        return [
            {
                "name": name,
                "description": data["manifest"].description,
                "version": data["manifest"].version,
                "author": data["manifest"].author,
            }
            for name, data in tools.items()
        ]

    def list_providers(self) -> List[Dict[str, str]]:
        """List all providers with their metadata."""
        providers = self.get_providers()
        return [
            {
                "name": name,
                "description": data["manifest"].description,
                "version": data["manifest"].version,
                "author": data["manifest"].author,
            }
            for name, data in providers.items()
        ]

    def reload(self) -> None:
        """Reload all plugins."""
        self._tools.clear()
        self._providers.clear()
        self._loaded = False
        self.discover_all()
        logger.info("Plugins reloaded")