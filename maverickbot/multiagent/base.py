"""Base agent class for multi-agent system."""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from loguru import logger

from maverickbot.providers.base import LLMProvider
from maverickbot.agent.tools.registry import ToolRegistry


class AgentRole(Enum):
    SUPERVISOR = "supervisor"
    WORKER = "worker"
    REFLECTOR = "reflector"


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    name: str
    role: AgentRole
    system_prompt: str
    model: Optional[str] = None
    max_iterations: int = 10
    timeout: int = 120
    capabilities: List[str] = None
    tools: List[str] = None

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.tools is None:
            self.tools = []


class BaseAgent(ABC):
    """Base class for all agents in the multi-agent system."""

    def __init__(
        self,
        config: AgentConfig,
        provider: LLMProvider,
        tool_registry: ToolRegistry,
        message_bus=None,
    ):
        self.config = config
        self.provider = provider
        self.tool_registry = tool_registry
        self.message_bus = message_bus
        self.name = config.name
        self.role = config.role
        self._active = False

    @abstractmethod
    async def initialize(self):
        """Initialize the agent."""
        pass

    @abstractmethod
    async def process(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task and return result."""
        pass

    async def activate(self):
        """Activate the agent."""
        self._active = True
        if self.message_bus:
            self.message_bus.subscribe(self.name, self._handle_message)
        logger.info(f"Agent {self.name} activated")

    async def deactivate(self):
        """Deactivate the agent."""
        self._active = False
        if self.message_bus:
            self.message_bus.unsubscribe(self.name)
        logger.info(f"Agent {self.name} deactivated")

    async def _handle_message(self, message):
        """Handle incoming messages."""
        if message.receiver == self.name or message.receiver is None:
            logger.debug(f"Agent {self.name} received message: {message.type}")
            await self._on_message(message)

    async def _on_message(self, message):
        """Override to handle specific message types."""
        pass

    def is_active(self) -> bool:
        return self._active

    async def chat(self, messages: List[Dict[str, str]], tools: bool = True) -> str:
        """Helper to chat with LLM."""
        from maverickbot.agent.tools.base import ToolResult

        tool_schemas = None
        if tools and self.tool_registry:
            tool_schemas = self.tool_registry.get_schemas()

        response = await self.provider.chat(
            messages=messages,
            tools=tool_schemas if tool_schemas else None,
        )
        return response.content