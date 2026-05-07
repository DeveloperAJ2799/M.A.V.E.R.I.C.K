"""Read file tool."""

import os
from typing import Any, Dict
from .base import Tool, ToolResult


class ReadFileTool(Tool):
    """Tool for reading file contents."""

    def __init__(self):
        super().__init__(
            name="read_file",
            description="Read the contents of a file.",
        )

    async def execute(self, file_path: str, **kwargs) -> ToolResult:
        try:
            if not os.path.exists(file_path):
                return ToolResult(
                    success=False, result=None, error=f"File not found: {file_path}"
                )
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return ToolResult(success=True, result=content)
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to read",
                }
            },
            "required": ["file_path"],
        }