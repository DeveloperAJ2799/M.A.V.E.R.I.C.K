"""CLI package."""
import asyncio
import sys

from .config import CLIConfig, ConfigManager
from .commands.base import Command, CommandManager
from .commands.chat import ChatCommand
from .commands.list import ListCommand
from .commands.config import ConfigCommand
from .commands.init import InitCommand
from .runner import CLI


def main():
    """Main entry point for CLI."""
    cli = CLI()
    try:
        asyncio.run(cli.run())
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


__all__ = [
    "CLIConfig",
    "ConfigManager",
    "Command",
    "CommandManager",
    "ChatCommand",
    "ListCommand", 
    "ConfigCommand",
    "InitCommand",
    "main",
]