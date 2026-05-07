"""Git integration tools."""
import asyncio
import subprocess
from typing import Any, Dict
from .base import Tool, ToolResult


class GitStatusTool(Tool):
    """Tool for git status."""

    def __init__(self):
        super().__init__(
            name="git_status",
            description="Show git repository status. Input: JSON with optional 'path' (default: current dir).",
        )

    async def execute(self, **kwargs) -> ToolResult:
        path = kwargs.get("path", ".")
        
        try:
            result = await asyncio.create_subprocess_shell(
                f"cd {path} && git status",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                return ToolResult(success=True, result=stdout.decode())
            else:
                return ToolResult(success=False, result=None, error=stderr.decode() or "Not a git repo")
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to git repository (default: current dir)"}
            }
        }


class GitLogTool(Tool):
    """Tool for git log."""

    def __init__(self):
        super().__init__(
            name="git_log",
            description="Show recent git commits. Input: JSON with optional 'path' and 'limit'.",
        )

    async def execute(self, **kwargs) -> ToolResult:
        path = kwargs.get("path", ".")
        limit = kwargs.get("limit", 10)
        
        try:
            result = await asyncio.create_subprocess_shell(
                f"cd {path} && git log --oneline -n {limit}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                return ToolResult(success=True, result=stdout.decode() or "No commits yet")
            else:
                return ToolResult(success=False, result=None, error=stderr.decode())
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to git repository"},
                "limit": {"type": "integer", "description": "Number of commits to show (default: 10)"}
            }
        }


class GitDiffTool(Tool):
    """Tool for git diff."""

    def __init__(self):
        super().__init__(
            name="git_diff",
            description="Show git diff. Input: JSON with optional 'path', 'file' (specific file), 'staged' (boolean).",
        )

    async def execute(self, **kwargs) -> ToolResult:
        path = kwargs.get("path", ".")
        file = kwargs.get("file", "")
        staged = kwargs.get("staged", False)
        
        cmd = f"cd {path} && git diff"
        if staged:
            cmd = f"cd {path} && git diff --staged"
        if file:
            cmd += f" -- {file}"
        
        try:
            result = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                output = stdout.decode() or "No changes"
                if len(output) > 5000:
                    output = output[:5000] + "\n... (truncated)"
                return ToolResult(success=True, result=output)
            else:
                return ToolResult(success=False, result=None, error=stderr.decode())
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to git repository"},
                "file": {"type": "string", "description": "Specific file to diff"},
                "staged": {"type": "boolean", "description": "Show staged changes"}
            }
        }


class GitBranchTool(Tool):
    """Tool for git branch."""

    def __init__(self):
        super().__init__(
            name="git_branch",
            description="List git branches. Input: JSON with optional 'path', 'create' (new branch name), 'delete' (branch to delete).",
        )

    async def execute(self, **kwargs) -> ToolResult:
        path = kwargs.get("path", ".")
        create = kwargs.get("create", "")
        delete = kwargs.get("delete", "")
        
        if create:
            cmd = f"cd {path} && git checkout -b {create}"
        elif delete:
            cmd = f"cd {path} && git branch -d {delete}"
        else:
            cmd = f"cd {path} && git branch -a"
        
        try:
            result = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                return ToolResult(success=True, result=stdout.decode())
            else:
                return ToolResult(success=False, result=None, error=stderr.decode())
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to git repository"},
                "create": {"type": "string", "description": "Create new branch"},
                "delete": {"type": "string", "description": "Delete branch"}
            }
        }