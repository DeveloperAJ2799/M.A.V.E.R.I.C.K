"""Tool registry."""

from typing import Dict, List, Any, Optional
from .base import Tool, ToolResult


class ToolRegistry:
    """Registry for available tools."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())

    def get_schemas(self) -> List[Dict[str, Any]]:
        return [tool.get_schema() for tool in self._tools.values()]

    async def execute(self, tool_name: str, **kwargs) -> ToolResult:
        tool = self.get(tool_name)
        if not tool:
            return ToolResult(
                success=False, result=None, error=f"Tool not found: {tool_name}"
            )
        try:
            result = await tool.execute(**kwargs)
            return result
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))