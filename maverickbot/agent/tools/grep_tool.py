"""Grep tool for searching file contents."""
import os
import re
from typing import Any, Dict
from .base import Tool, ToolResult


class GrepTool(Tool):
    """Tool for searching file contents using regex."""

    def __init__(self):
        super().__init__(
            name="grep",
            description="Search for a pattern in files. Returns matching lines with context.",
        )

    async def execute(
        self,
        pattern: str,
        path: str = ".",
        file_pattern: str = "*",
        case_sensitive: bool = False,
        context_lines: int = 2,
        max_results: int = 100,
        **kwargs
    ) -> ToolResult:
        try:
            matches = []
            regex = re.compile(pattern, re.IGNORECASE if not case_sensitive else 0)
            
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', '.git', 'venv', 'env']]
                
                for file in files:
                    if not self._match_file(file, file_pattern):
                        continue
                    
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                        
                        file_matches = []
                        for i, line in enumerate(lines, 1):
                            if regex.search(line):
                                file_matches.append((i, line.rstrip()))
                                if len(file_matches) >= max_results:
                                    break
                        
                        if file_matches:
                            matches.append(f"\n📄 {filepath}")
                            for line_num, content in file_matches:
                                prefix = "  " if context_lines > 0 else ""
                                matches.append(f"{prefix}→ {line_num}: {content}")
                                
                    except (PermissionError, IsADirectoryError):
                        continue
                    except Exception:
                        continue
                    
                    if len(matches) >= max_results * 3:
                        matches.append(f"\n... (results truncated at {max_results})")
                        break
                
                if len(matches) >= max_results * 3:
                    break
            
            if not matches:
                return ToolResult(success=True, result=f"No matches found for '{pattern}' in {path}")
            
            return ToolResult(success=True, result="\n".join(matches))
        
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _match_file(self, filename: str, pattern: str) -> bool:
        """Check if filename matches the pattern."""
        if pattern == "*" or pattern == "*.*":
            return True
        
        if "*" in pattern:
            import fnmatch
            return fnmatch.fnmatch(filename, pattern)
        
        return pattern in filename

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The regex pattern to search for",
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in (default: current directory)",
                },
                "file_pattern": {
                    "type": "string",
                    "description": "File pattern to match (e.g., '*.py', '*.js', default: '*')",
                },
                "case_sensitive": {
                    "type": "boolean",
                    "description": "Whether to match case (default: false)",
                },
                "context_lines": {
                    "type": "integer",
                    "description": "Number of context lines around matches (default: 2)",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results (default: 100)",
                },
            },
            "required": ["pattern"],
        }
