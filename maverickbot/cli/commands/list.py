"""List command - show available resources."""
import asyncio
import argparse
from typing import Optional, Any

from maverickbot.providers import ProviderRegistry
from maverickbot.core import Registry
from maverickbot.multiagent import MultiAgentOrchestrator
from maverickbot.agent import ToolRegistry
from maverickbot.agent.tools import (
    ReadFileTool, WriteFileTool, AppendFileTool, ShellTool, SearchTool
)
from .base import Command


class ListCommand(Command):
    """List available resources command."""

    name = "list"
    help = "List available models, plugins, skills, or agents"
    aliases = ["ls", "l"]

    def __init__(self):
        self.parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog="maverickbot list")
        parser.add_argument(
            "resource",
            choices=["models", "plugins", "skills", "agents", "all"],
            help="Resource to list",
        )
        parser.add_argument("--provider", "-p", default="lmstudio", help="Provider name")
        parser.add_argument("--url", "-u", default="http://127.0.0.1:1234", help="Provider URL")
        return parser

    async def execute(self, args: argparse.Namespace, context: dict) -> Optional[Any]:
        """Execute the list command."""
        from colorama import Fore, Style
        
        if args.resource in ["models", "all"]:
            await self._list_models(args, Fore, Style)
        
        if args.resource in ["plugins", "all"]:
            self._list_plugins(Fore, Style)
        
        if args.resource in ["skills", "all"]:
            self._list_skills(Fore, Style)
        
        if args.resource in ["agents", "all"]:
            await self._list_agents(args, Fore, Style)

    async def _list_models(self, args, Fore, Style):
        """List available models."""
        print(f"\n{Fore.CYAN}=== Available Models ==={Style.RESET_ALL}")
        
        provider = ProviderRegistry.create(args.provider, base_url=args.url)
        
        try:
            models = await provider.list_models()
            for model in models:
                print(f"  {Fore.YELLOW}• {model}{Style.RESET_ALL}")
        except Exception as e:
            print(f"  {Fore.RED}Error: {e}{Style.RESET_ALL}")

    def _list_plugins(self, Fore, Style):
        """List available plugins."""
        print(f"\n{Fore.CYAN}=== Available Plugins ==={Style.RESET_ALL}")
        
        registry = Registry()
        registry.initialize()
        
        tools = registry.list_tools()
        if tools:
            print(f"  {Fore.GREEN}Tools:{Style.RESET_ALL}")
            for tool in tools:
                print(f"    {Fore.YELLOW}{tool['name']}{Style.RESET_ALL} - {tool['description']}")
        else:
            print(f"  No custom tools")
        
        providers = registry.list_providers()
        if providers:
            print(f"  {Fore.GREEN}Providers:{Style.RESET_ALL}")
            for p in providers:
                print(f"    {Fore.YELLOW}{p['name']}{Style.RESET_ALL} - {p['description']}")
        else:
            print(f"  No custom providers")

    def _list_skills(self, Fore, Style):
        """List available skills."""
        print(f"\n{Fore.CYAN}=== Available Skills ==={Style.RESET_ALL}")
        
        registry = Registry()
        registry.initialize()
        
        skills = registry.list_skills()
        if skills:
            for skill in skills:
                print(f"  {Fore.YELLOW}{skill['name']}{Style.RESET_ALL} v{skill['version']}")
                print(f"    {skill['description']}")
                print(f"    Tools: {skill['tools']}")
        else:
            print(f"  No skills available")
        print(f"\n  Use /skill <name> in chat to activate")

    async def _list_agents(self, args, Fore, Style):
        """List multi-agent workers."""
        print(f"\n{Fore.CYAN}=== Multi-Agent System ==={Style.RESET_ALL}")
        
        provider = ProviderRegistry.create(args.provider, base_url=args.url)
        tool_registry = ToolRegistry()
        
        orchestrator = MultiAgentOrchestrator(
            provider=provider,
            tool_registry=tool_registry,
        )
        await orchestrator.initialize()
        
        agents = orchestrator.list_agents()
        for agent in agents:
            print(f"  {Fore.YELLOW}{agent['name']}{Style.RESET_ALL} ({agent['role']})")
            print(f"    Capabilities: {agent['capabilities']}")