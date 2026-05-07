"""Session manager for agent conversations."""
import uuid
from typing import List, Dict, Optional


class Session:
    """Single conversation session."""

    def __init__(self, id: str, system_prompt: str):
        self.id = id
        self.system_prompt = system_prompt
        self.messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt}
        ]

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})

    def get_messages(self) -> List[Dict[str, str]]:
        return self.messages

    def replace_messages(self, messages: List[Dict[str, str]]) -> None:
        self.messages = messages

    def clear(self) -> None:
        self.messages = [
            {"role": "system", "content": self.system_prompt}
        ]


class SessionManager:
    """Manages agent conversation sessions."""

    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.current_session_id: Optional[str] = None

    def create_session(self, system_prompt: str = "You are a helpful AI assistant.") -> Session:
        session_id = str(uuid.uuid4())
        session = Session(session_id, system_prompt)
        self.sessions[session_id] = session
        self.current_session_id = session_id
        return session

    def get_current_session(self) -> Optional[Session]:
        if not self.current_session_id:
            return None
        return self.sessions.get(self.current_session_id)

    def add_message(self, role: str, content: str) -> None:
        session = self.get_current_session()
        if session:
            session.add_message(role, content)

    def get_messages(self) -> List[Dict[str, str]]:
        session = self.get_current_session()
        return session.get_messages() if session else []

    def replace_messages(self, messages: List[Dict[str, str]]) -> None:
        session = self.get_current_session()
        if session:
            session.replace_messages(messages)

    def clear(self) -> None:
        session = self.get_current_session()
        if session:
            session.clear()

    def switch_session(self, session_id: str) -> Optional[Session]:
        if session_id in self.sessions:
            self.current_session_id = session_id
            return self.sessions[session_id]
        return None

    def list_sessions(self) -> List[str]:
        return list(self.sessions.keys())