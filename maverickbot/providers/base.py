"""LLM provider base."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class LLMResponse:
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, model: str):
        self.model = model

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """Send a chat message and get a response."""
        pass

    @abstractmethod
    async def list_models(self) -> List[str]:
        """List available models."""
        pass