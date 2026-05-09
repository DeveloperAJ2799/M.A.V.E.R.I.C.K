"""Edit tool for in-place file modifications."""
import os
import difflib
from typing import Any, Dict
from .base import Tool, ToolResult


class EditFileTool(Tool):
    """Tool for editing files in-place using oldString/newString replacement."""

    def __init__(self):
        super().__init__(
            name="edit_file",
            description="Edit a file by replacing oldString with newString. Use for making targeted changes to code or text files.",
        )

    async def execute(
        self,
        file_path: str,
        oldString: str,
        newString: str,
        **kwargs
    ) -> ToolResult:
        try:
            if not os.path.exists(file_path):
                return ToolResult(success=False, result=None, error=f"File not found: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if oldString not in content:
                return ToolResult(
                    success=False,
                    result=None,
                    error=f"oldString not found in file. Make sure to use the exact text including indentation."
                )
            
            new_content = content.replace(oldString, newString, 1)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return ToolResult(
                success=True,
                result=f"Successfully edited {file_path}"
            )
        
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to edit",
                },
                "oldString": {
                    "type": "string",
                    "description": "The exact text to find and replace (must match exactly, including whitespace)",
                },
                "newString": {
                    "type": "string",
                    "description": "The replacement text",
                },
            },
            "required": ["file_path", "oldString", "newString"],
        }


class ReplaceAllTool(Tool):
    """Tool for replacing all occurrences of a string in a file."""

    def __init__(self):
        super().__init__(
            name="replace_all",
            description="Replace all occurrences of oldString with newString in a file.",
        )

    async def execute(
        self,
        file_path: str,
        oldString: str,
        newString: str,
        **kwargs
    ) -> ToolResult:
        try:
            if not os.path.exists(file_path):
                return ToolResult(success=False, result=None, error=f"File not found: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            count = content.count(oldString)
            if count == 0:
                return ToolResult(
                    success=False,
                    result=None,
                    error="oldString not found in file"
                )
            
            new_content = content.replace(oldString, newString)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return ToolResult(
                success=True,
                result=f"Replaced {count} occurrence(s) in {file_path}"
            )
        
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to edit",
                },
                "oldString": {
                    "type": "string",
                    "description": "The text to find and replace",
                },
                "newString": {
                    "type": "string",
                    "description": "The replacement text",
                },
            },
            "required": ["file_path", "oldString", "newString"],
        }
