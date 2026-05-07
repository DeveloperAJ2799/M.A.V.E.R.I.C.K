"""Main CLI runner."""
import asyncio
import argparse
import sys
from typing import Optional

from loguru import logger

from maverickbot.cli.config import ConfigManager
from maverickbot.cli.commands import (
    CommandManager,
    ChatCommand,
    ListCommand,
    ConfigCommand,
    InitCommand,
)


class CLI:
    """Main CLI application."""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.command_manager = CommandManager()
        self._register_commands()

    def _register_commands(self):
        """Register all available commands."""
        from maverickbot.cli.commands import (
            ChatCommand, ListCommand, ConfigCommand, InitCommand
        )
        from maverickbot.cli.commands.session_cmd import SessionCommand
        self.command_manager.register(ChatCommand())
        self.command_manager.register(ListCommand())
        self.command_manager.register(ConfigCommand())
        self.command_manager.register(InitCommand())
        self.command_manager.register(SessionCommand())

    async def run(self, args: list = None):
        """Run the CLI."""
        if args is None:
            import sys
            args = sys.argv[1:]
        
        parser = self._build_parser()
        
        # Handle --interactive as default command
        interactive_mode = '--interactive' in args or '-i' in args
        if interactive_mode:
            args = [a for a in args if a not in ['--interactive', '-i']]
            if args:
                if args[0] in ['chat', 'c', 'shell', 'list', 'ls', 'l', 'config', 'cfg', 'init', 'i']:
                    pass  # Keep existing command
                else:
                    args.insert(0, 'chat')
            else:
                args = ['chat']
        
        if not args:
            from maverickbot.cli.banner import print_banner
            print_banner()
            print()
            parser.print_help()
            self._print_available_commands()
            return
        
        # Get the command first
        command_name = args[0]
        if command_name not in ['chat', 'c', 'shell', 'list', 'ls', 'l', 'config', 'cfg', 'init', 'i', 'session', 'mem']:
            parser.print_help()
            self._print_available_commands()
            return
        
        remaining = args[1:] if len(args) > 1 else []
        
        config = self.config_manager.load()
        self._setup_logging(config.log_level, config.debug)
        
        command = self.command_manager.get(command_name)
        if command:
            context = {"config": config, "cli": self}
            await command.execute_with_args(remaining, context)
        else:
            print(f"Unknown command: {command_name}")
            parser.print_help()

    def _print_available_commands(self):
        print("""
Available commands:
  chat, c, shell    - Start interactive chat
  list, ls, l       - List available resources
  config, cfg       - Manage configuration
  init, i          - Initialize project/skill/plugin
  session, mem      - Manage sessions and memory
        """)

    def _build_parser(self) -> argparse.ArgumentParser:
        """Build the main argument parser."""
        parser = argparse.ArgumentParser(
            prog="maverickbot",
            description="M.A.V.E.R.I.C.K - AI Agent with multi-agent system",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        
        parser.add_argument(
            "--config", "-C",
            help="Path to config file",
        )
        
        parser.add_argument(
            "--interactive",
            action="store_true",
            default=False,
            help="Start interactive chat mode",
        )
        
        parser.add_argument(
            "command",
            nargs="?",
            default=None,
            choices=["chat", "c", "shell", "list", "ls", "l", "config", "cfg", "init", "i", "session", "mem"],
            help="Command to run",
        )
        
        return parser

    def _setup_logging(self, level: str, debug: bool):
        """Setup logging configuration."""
        logger.remove()
        
        if debug:
            logger.add(sys.stderr, level="DEBUG")
        else:
            level_map = {
                "DEBUG": "DEBUG",
                "INFO": "INFO",
                "WARNING": "WARNING",
                "ERROR": "ERROR",
            }
            logger.add(sys.stderr, level=level_map.get(level.upper(), "ERROR"))


def main():
    """Entry point for the CLI."""
    cli = CLI()
    
    try:
        asyncio.run(cli.run())
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()