"""Multi-agent system for M.A.V.E.R.I.C.K v2.0."""
from .orchestrator import MultiAgentOrchestrator
from .base import BaseAgent, AgentConfig, AgentRole
from .supervisor import SupervisorAgent
from .worker import WorkerAgent
from .message_bus import MessageBus, AgentMessage, MessageType

__all__ = [
    "MultiAgentOrchestrator",
    "BaseAgent",
    "AgentConfig",
    "AgentRole",
    "SupervisorAgent",
    "WorkerAgent",
    "MessageBus",
    "AgentMessage",
    "MessageType",
]