"""My custom tool plugin."""
from typing import Any, Dict
from maverickbot.agent.tools.base import Tool, ToolResult


class MyTool(Tool):
    """Custom tool for a specific task."""

    def __init__(self):
        super().__init__(
            name="my_tool",
            description="Description of what this tool does and what arguments it accepts"
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given arguments."""
        try:
            # Your tool logic here
            # Access args via kwargs, e.g., kwargs.get("input")
            
            result = f"Tool executed with: {kwargs}"
            return ToolResult(success=True, result=result)
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        """Return the parameters schema for LLM function calling."""
        return {
            "type": "object",
            "properties": {
                "input": {
                    "type": "string",
                    "description": "Input description"
                },
                "option": {
                    "type": "string",
                    "description": "Optional parameter",
                    "enum": ["option1", "option2", "option3"]
                }
            },
            "required": ["input"]
        }