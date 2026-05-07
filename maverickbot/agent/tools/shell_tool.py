"""Shell tool for executing commands."""

import asyncio
from typing import Any, Dict
from .base import Tool, ToolResult


class ShellTool(Tool):
    """Tool for executing shell commands."""

    def __init__(self):
        super().__init__(
            name="shell",
            description="Execute a shell command and return the output.",
        )

    async def execute(self, command: str, **kwargs) -> ToolResult:
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            output = stdout.decode("utf-8", errors="replace")
            if stderr:
                output += "\n[stderr]: " + stderr.decode("utf-8", errors="replace")
            return ToolResult(success=True, result=output)
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                }
            },
            "required": ["command"],
        }