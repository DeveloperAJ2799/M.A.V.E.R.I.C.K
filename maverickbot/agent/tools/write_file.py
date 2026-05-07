"""Write file tool."""

import os
from typing import Any, Dict
from .base import Tool, ToolResult


class WriteFileTool(Tool):
    """Tool for writing content to a file."""

    def __init__(self):
        super().__init__(
            name="write_file",
            description="Write content to a file. Creates the file if it doesn't exist, overwrites if it does.",
        )

    async def execute(self, file_path: str, content: str, append: bool = False, **kwargs) -> ToolResult:
        try:
            dir_path = os.path.dirname(file_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            mode = "a" if append else "w"
            with open(file_path, mode, encoding="utf-8") as f:
                f.write(content)
            action = "appended to" if append else "wrote to"
            return ToolResult(success=True, result=f"Successfully {action} {file_path}")
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to write",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file",
                },
                "append": {
                    "type": "boolean",
                    "description": "If true, append to the file instead of overwriting",
                    "default": False,
                }
            },
            "required": ["file_path", "content"],
        }


class AppendFileTool(Tool):
    """Tool for appending content to a file."""

    def __init__(self):
        super().__init__(
            name="append_file",
            description="Append content to a file. Creates the file if it doesn't exist.",
        )

    async def execute(self, file_path: str, content: str, **kwargs) -> ToolResult:
        try:
            dir_path = os.path.dirname(file_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(content)
            return ToolResult(success=True, result=f"Successfully appended to {file_path}")
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to append to",
                },
                "content": {
                    "type": "string",
                    "description": "The content to append to the file",
                }
            },
            "required": ["file_path", "content"],
        }