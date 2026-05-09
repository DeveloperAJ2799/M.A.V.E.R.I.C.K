"""Glob tool for finding files by pattern."""
import os
import fnmatch
from typing import Any, Dict, List
from .base import Tool, ToolResult


class GlobTool(Tool):
    """Tool for finding files matching a pattern."""

    def __init__(self):
        super().__init__(
            name="glob",
            description="Find files matching a glob pattern. Returns relative paths.",
        )

    async def execute(
        self,
        pattern: str = "*",
        path: str = ".",
        max_results: int = 100,
        include_hidden: bool = False,
        **kwargs
    ) -> ToolResult:
        try:
            matches: List[str] = []
            count = 0
            
            for root, dirs, files in os.walk(path):
                if not include_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                    files = [f for f in files if not f.startswith('.')]
                
                dirs[:] = [d for d in dirs if d not in ['node_modules', '__pycache__', '.git', 'venv', 'env', '.venv']]
                
                for file in files:
                    if fnmatch.fnmatch(file, pattern) or fnmatch.fnmatch(file, f"*{pattern}*"):
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, path)
                        matches.append(rel_path)
                        count += 1
                        
                        if count >= max_results:
                            matches.append(f"\n... (showing {max_results} of {count}+ files)")
                            return ToolResult(success=True, result="\n".join(matches))
            
            if not matches:
                return ToolResult(success=True, result=f"No files matching '{pattern}' found in {path}")
            
            return ToolResult(success=True, result="\n".join(matches))
        
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to match (e.g., '*.py', '**/*.js', default: '*')",
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in (default: current directory)",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of files to return (default: 100)",
                },
                "include_hidden": {
                    "type": "boolean",
                    "description": "Include hidden files (default: false)",
                },
            },
        }
