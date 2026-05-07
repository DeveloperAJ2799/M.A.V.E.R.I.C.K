"""Session management command."""
import argparse
import asyncio
from pathlib import Path
from typing import Optional, Any

from .base import Command
from maverickbot.cli.commands.session import SessionManager


class SessionCommand(Command):
    """Session management command."""

    name = "session"
    help = "Manage chat sessions and persistent memory"
    aliases = ["mem"]

    def __init__(self):
        self.parser = self._create_parser()
        self.manager = SessionManager()

    def _create_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog="maverickbot session")
        
        parser.add_argument("action", nargs="?", choices=["list", "save", "load", "delete", "memory", "remember", "clear"], default="list")
        parser.add_argument("name", nargs="?", help="Session name or key")
        parser.add_argument("value", nargs="?", help="Value for remember")
        
        return parser

    async def execute(self, args: argparse.Namespace, context: dict) -> Optional[Any]:
        """Execute session command."""
        action = args.action
        
        if action == "list":
            sessions = self.manager.list_sessions()
            if sessions:
                print("Saved sessions:")
                for s in sessions:
                    print(f"  - {s}")
            else:
                print("No saved sessions")
        
        elif action == "save":
            name = args.name
            if not name:
                print("Usage: session save <name>")
                return
            print(f"To save current session, use /save command in chat")
        
        elif action == "load":
            name = args.name
            if not name:
                print("Usage: session load <name>")
                return
            session = self.manager.load_session(name)
            if session:
                print(f"Loaded: {session['name']} ({session['timestamp']})")
            else:
                print(f"Session '{name}' not found")
        
        elif action == "delete":
            name = args.name
            if not name:
                print("Usage: session delete <name>")
                return
            self.manager.delete_session(name)
            print(f"Deleted: {name}")
        
        elif action == "memory":
            if args.name == "clear":
                self.manager.memory = {"preferences": {}, "facts": {}}
                self.manager._save_memory()
                print("Memory cleared")
            else:
                prefs = self.manager.get_preferences()
                if prefs:
                    print("Remembered preferences:")
                    for k, v in prefs.items():
                        print(f"  {k}: {v}")
                else:
                    print("No remembered preferences")
        
        elif action == "remember":
            if not args.name or not args.value:
                print("Usage: session remember <key> <value>")
                return
            self.manager.remember(args.name, args.value, "preference")
            print(f"Remembered: {args.name} = {args.value}")