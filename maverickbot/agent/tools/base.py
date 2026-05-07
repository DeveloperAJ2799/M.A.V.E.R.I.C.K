"""Base tool class."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass


@dataclass
class ToolResult:
    success: bool
    result: Any
    error: Optional[str] = None


class Tool(ABC):
    """Abstract base class for tools."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given arguments."""
        pass

    def get_schema(self) -> Dict[str, Any]:
        """Return the tool's JSON schema for LLM function calling."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self._get_parameters_schema(),
            }
        }

    @abstractmethod
    def _get_parameters_schema(self) -> Dict[str, Any]:
        """Return the parameters schema."""
        pass