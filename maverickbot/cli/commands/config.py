"""Config command - manage CLI configuration."""
import asyncio
import argparse
from typing import Optional, Any

from maverickbot.cli.config import ConfigManager
from .base import Command


class ConfigCommand(Command):
    """Config management command."""

    name = "config"
    help = "Manage CLI configuration"
    aliases = ["cfg"]

    def __init__(self):
        self.parser = self._create_parser()
        self.config_manager = ConfigManager()

    def _create_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog="maverickbot config")
        sub = parser.add_subparsers(dest="action", help="Config action")
        
        get_parser = sub.add_parser("get", help="Get config value")
        get_parser.add_argument("key", help="Config key to get")
        
        set_parser = sub.add_parser("set", help="Set config value")
        set_parser.add_argument("key", help="Config key")
        set_parser.add_argument("value", help="Config value")
        
        sub.add_parser("list", help="List all config values")
        sub.add_parser("init", help="Initialize default config file")
        sub.add_parser("edit", help="Open config file in editor")
        
        return parser

    async def execute(self, args: argparse.Namespace, context: dict) -> Optional[Any]:
        """Execute the config command."""
        from colorama import Fore, Style
        
        self.config_manager.load()
        
        if args.action == "get":
            self._get_value(args.key, Fore, Style)
        elif args.action == "set":
            self._set_value(args.key, args.value, Fore, Style)
        elif args.action == "list":
            self._list_config(Fore, Style)
        elif args.action == "init":
            self._init_config(Fore, Style)
        elif args.action == "edit":
            self._edit_config(Fore, Style)

    def _get_value(self, key: str, Fore, Style):
        """Get a config value."""
        if hasattr(self.config_manager.config, key):
            value = getattr(self.config_manager.config, key)
            print(f"{key} = {value}")
        else:
            print(f"{Fore.RED}Unknown config key: {key}{Style.RESET_ALL}")
            print(f"Available: provider, model, lmurl, temperature, max_tokens, system_prompt, multi_agent")

    def _set_value(self, key: str, value: str, Fore, Style):
        """Set a config value."""
        if not hasattr(self.config_manager.config, key):
            print(f"{Fore.RED}Unknown config key: {key}{Style.RESET_ALL}")
            return

        type_fn = type(getattr(self.config_manager.config, key))
        try:
            if type_fn == bool:
                value = value.lower() in ("true", "1", "yes")
            else:
                value = type_fn(value)
            
            self.config_manager.config = self.config_manager.config.__class__(**{
                k: v if k != key else value 
                for k, v in vars(self.config_manager.config).items()
            })
            print(f"{Fore.GREEN}Set {key} = {value}{Style.RESET_ALL}")
        except ValueError:
            print(f"{Fore.RED}Invalid value for {key}: {value}{Style.RESET_ALL}")

    def _list_config(self, Fore, Style):
        """List all config values."""
        print(f"\n{Fore.CYAN}=== Current Configuration ==={Style.RESET_ALL}")
        
        config_vars = vars(self.config_manager.config)
        for key, value in config_vars.items():
            print(f"  {Fore.YELLOW}{key}{Style.RESET_ALL}: {value}")

    def _init_config(self, Fore, Style):
        """Initialize default config file."""
        from pathlib import Path
        
        config_path = Path.cwd() / "maverickbot.yaml"
        if config_path.exists():
            print(f"{Fore.YELLOW}Config already exists at {config_path}{Style.RESET_ALL}")
            return
        
        self.config_manager.save(config_path)
        print(f"{Fore.GREEN}Created config at {config_path}{Style.RESET_ALL}")

    def _edit_config(self, Fore, Style):
        """Open config in editor."""
        import os
        from pathlib import Path
        
        config_path = Path.cwd() / "maverickbot.yaml"
        
        if not config_path.exists():
            self.config_manager.save(config_path)
        
        editor = os.environ.get("EDITOR", "notepad" if os.name == "nt" else "vim")
        os.system(f'{editor} "{config_path}"')