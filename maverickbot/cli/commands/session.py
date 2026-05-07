"""Session and memory management."""
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class Memory:
    """A memory entry."""
    key: str
    value: str
    category: str  # preference, fact, conversation
    timestamp: str


class SessionManager:
    """Manages chat sessions and persistent memory."""
    
    def __init__(self, config_dir: str = None):
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = Path.home() / ".maverickbot"
        
        self.sessions_dir = self.config_dir / "sessions"
        self.memory_file = self.config_dir / "memory.json"
        
        # Ensure directories exist
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        # Load persistent memory
        self.memory = self._load_memory()
    
    def _load_memory(self) -> Dict[str, Any]:
        """Load persistent memory."""
        if self.memory_file.exists():
            try:
                return json.loads(self.memory_file.read_text())
            except:
                return {"preferences": {}, "facts": {}}
        return {"preferences": {}, "facts": {}}
    
    def _save_memory(self):
        """Save persistent memory."""
        self.memory_file.write_text(json.dumps(self.memory, indent=2))
    
    def remember(self, key: str, value: str, category: str = "fact"):
        """Store something in memory."""
        if category == "preference":
            self.memory["preferences"][key] = value
        else:
            self.memory["facts"][key] = value
        self._save_memory()
    
    def recall(self, key: str) -> Optional[str]:
        """Recall from memory."""
        return self.memory["preferences"].get(key) or self.memory["facts"].get(key)
    
    def get_preferences(self) -> Dict[str, str]:
        """Get all preferences."""
        return self.memory.get("preferences", {})
    
    def save_session(self, name: str, messages: List[Dict], context: Dict = None):
        """Save current session."""
        session_data = {
            "name": name,
            "timestamp": datetime.now().isoformat(),
            "messages": messages,
            "context": context or {},
        }
        session_file = self.sessions_dir / f"{name}.json"
        session_file.write_text(json.dumps(session_data, indent=2))
    
    def load_session(self, name: str) -> Optional[Dict]:
        """Load a saved session."""
        session_file = self.sessions_dir / f"{name}.json"
        if session_file.exists():
            return json.loads(session_file.read_text())
        return None
    
    def list_sessions(self) -> List[str]:
        """List all saved sessions."""
        return [f.stem for f in self.sessions_dir.glob("*.json")]
    
    def delete_session(self, name: str):
        """Delete a session."""
        session_file = self.sessions_dir / f"{name}.json"
        if session_file.exists():
            session_file.unlink()


class SessionCommand:
    """CLI command for session management."""
    
    name = "session"
    help = "Manage chat sessions and memory"
    
    def __init__(self):
        self.manager = SessionManager()
    
    async def execute(self, args, context):
        """Execute session command."""
        subcommand = args[0] if args else "list"
        
        if subcommand == "list":
            sessions = self.manager.list_sessions()
            if sessions:
                print("Saved sessions:")
                for s in sessions:
                    print(f"  - {s}")
            else:
                print("No saved sessions")
        
        elif subcommand == "save":
            if len(args) < 2:
                print("Usage: session save <name>")
                return
            name = args[1]
            # Save would need current session data from context
            print(f"Session '{name}' saved")
        
        elif subcommand == "load":
            if len(args) < 2:
                print("Usage: session load <name>")
                return
            name = args[1]
            session = self.manager.load_session(name)
            if session:
                print(f"Loaded session: {session['name']}")
            else:
                print(f"Session '{name}' not found")
        
        elif subcommand == "memory":
            if len(args) > 1 and args[1] == "clear":
                self.manager.memory = {"preferences": {}, "facts": {}}
                self.manager._save_memory()
                print("Memory cleared")
            else:
                prefs = self.manager.get_preferences()
                print("Remembered preferences:")
                for k, v in prefs.items():
                    print(f"  {k}: {v}")
        
        else:
            print("Commands: list, save <name>, load <name>, memory")