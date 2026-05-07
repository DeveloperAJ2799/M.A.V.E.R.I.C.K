"""Base command class."""
from abc import ABC, abstractmethod
from typing import Any, Optional, List
import argparse


class Command(ABC):
    """Base class for CLI commands."""

    name: str = ""
    help: str = ""
    aliases: list = []

    def __init__(self):
        self.parser = self._create_parser()

    @abstractmethod
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser for this command."""
        pass

    @abstractmethod
    async def execute(self, args: argparse.Namespace, context: dict) -> Optional[Any]:
        """Execute the command."""
        pass

    async def execute_with_args(self, args: List[str], context: dict) -> Optional[Any]:
        """Execute command with raw args list."""
        parsed = self.parser.parse_args(args)
        return await self.execute(parsed, context)


class CommandManager:
    """Manages all CLI commands."""

    def __init__(self):
        self._commands: dict = {}

    def register(self, command: Command):
        """Register a command."""
        self._commands[command.name] = command
        for alias in command.aliases:
            self._commands[alias] = command

    def get(self, name: str) -> Optional[Command]:
        """Get a command by name."""
        return self._commands.get(name)

    def list_commands(self) -> list:
        """List all available commands."""
        return [(cmd.name, cmd.help) for cmd in self._commands.values()]


class CommandManager:
    """Manages all CLI commands."""

    def __init__(self):
        self._commands: dict = {}

    def register(self, command: Command):
        """Register a command."""
        self._commands[command.name] = command
        for alias in command.aliases:
            self._commands[alias] = command

    def get(self, name: str) -> Optional[Command]:
        """Get a command by name."""
        return self._commands.get(name)

    def list_commands(self) -> list:
        """List all available commands."""
        return [(cmd.name, cmd.help) for cmd in self._commands.values()]

    def get_parser(self) -> argparse.ArgumentParser:
        """Get the main parser with all subcommands."""
        parser = argparse.ArgumentParser(
            prog="maverickbot",
            description="M.A.V.E.R.I.C.K - AI Agent with multi-agent system",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        
        subparsers = parser.add_subparsers(dest="command", help="Available commands")
        
        for command in self._commands.values():
            command.add_subparser(subparsers)
        
        return parser