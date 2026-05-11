"""Friendly response formatter for non-technical users."""
import os
import re
from pathlib import Path
from typing import Any, Optional, Dict

from .constants import SIMPLE_LANGUAGE


class FriendlyResponse:
    """Convert technical output to friendly, understandable messages."""
    
    def __init__(self):
        self.tool_translations = {
            "create_pdf": "create a PDF",
            "read_pdf": "read a PDF",
            "read_file": "read a file",
            "write_file": "write a file",
            "execute_code": "run code",
            "shell": "run a command",
            "workspace": "manage your workspace",
        }
    
    def format_success(self, tool: str, result: str, file_path: Optional[str] = None) -> str:
        """Format a successful tool result for non-technical users."""
        # Translate tool name
        friendly_tool = self.tool_translations.get(tool, tool)
        
        lines = []
        
        # Main message
        if tool == "create_pdf":
            lines.append("Done! I've created your PDF.")
        elif tool == "read_pdf":
            lines.append("Here's the content from that PDF:")
            lines.append("")
        elif tool == "read_file":
            lines.append("Here's what's in that file:")
            lines.append("")
        elif tool == "execute_code":
            lines.append("I've run the code for you. Here's the result:")
            lines.append("")
        else:
            lines.append(f"Done! {friendly_tool} completed.")
        
        # Add result content
        if result and tool in ["read_pdf", "read_file", "execute_code"]:
            lines.append(self._truncate_for_display(result))
        
        # Add file location
        if file_path:
            lines.append("")
            lines.append(f"The file is saved at:")
            lines.append(f"  {self._format_file_path(file_path)}")
        
        lines.append("")
        lines.append("What would you like to do next?")
        
        return "\n".join(lines)
    
    def format_error(self, tool: str, error: str, recovery_hint: str = None) -> str:
        """Format an error for non-technical users."""
        friendly_tool = self.tool_translations.get(tool, tool)
        
        # Simplify common errors
        error_lower = error.lower()
        
        lines = []
        
        if "not found" in error_lower or "no such file" in error_lower:
            lines.append("I couldn't find that file.")
            lines.append("")
            lines.append("Try:")
            lines.append("  • Check the file name spelling")
            lines.append("  • Drag the file into this window")
            lines.append("  • Or tell me the full path to the file")
        
        elif "empty" in error_lower or "no content" in error_lower:
            lines.append("The file appears to be empty.")
            lines.append("There might not be any readable text in it.")
        
        elif "permission" in error_lower:
            lines.append("I don't have permission to access that file.")
            lines.append("Try running this program as Administrator.")
        
        elif "timeout" in error_lower or "timed out" in error_lower:
            lines.append("This is taking too long. The operation timed out.")
            lines.append("Try again with a smaller file.")
        
        elif "connection" in error_lower or "network" in error_lower:
            lines.append("I couldn't connect to the server.")
            lines.append("Check your internet connection and try again.")
        
        elif "invalid" in error_lower:
            lines.append("Something seems wrong with the file format.")
            lines.append("It might be corrupted or not a valid PDF.")
        
        else:
            # Generic error with friendly message
            lines.append("Something went wrong.")
            lines.append("")
            lines.append(f"I tried to {friendly_tool}, but encountered a problem.")
            
            # Extract key info from error
            if recovery_hint:
                lines.append("")
                lines.append(f"Tip: {recovery_hint}")
        
        lines.append("")
        lines.append("What would you like to do instead?")
        
        return "\n".join(lines)
    
    def format_workflow_plan(self, steps: list, goal: str) -> str:
        """Format a workflow plan for non-technical users."""
        lines = []
        
        lines.append(f"I'll help you {goal}.")
        lines.append("")
        lines.append("Here's what I'll do:")
        lines.append("")
        
        for i, step in enumerate(steps, 1):
            description = step.get("description", step.get("tool_name", "do something"))
            lines.append(f"  {i}. {description}")
        
        lines.append("")
        lines.append("Is this okay? (yes/no)")
        
        return "\n".join(lines)
    
    def format_file_list(self, files: list) -> str:
        """Format a list of files for display."""
        if not files:
            return "I couldn't find any files."
        
        lines = []
        lines.append("Here are the files I found:")
        lines.append("")
        
        for file in files[:10]:  # Limit to 10
            name = file.get("name", "Unknown")
            size = file.get("size", 0)
            modified = file.get("modified", "")
            
            lines.append(f"  • {name}")
            if size:
                lines.append(f"    {self._format_size(size)}")
        
        if len(files) > 10:
            lines.append(f"  ... and {len(files) - 10} more files")
        
        lines.append("")
        lines.append("What would you like to do with these?")
        
        return "\n".join(lines)
    
    def simplify_technical_terms(self, text: str) -> str:
        """Replace technical terms with simple language."""
        result = text
        
        for technical, simple in SIMPLE_LANGUAGE.items():
            # Replace whole words only
            pattern = r'\b' + re.escape(technical) + r'\b'
            result = re.sub(pattern, simple, result, flags=re.IGNORECASE)
        
        return result
    
    def _truncate_for_display(self, text: str, max_lines: int = 50) -> str:
        """Truncate text for display while preserving readability."""
        if not text:
            return ""
        
        lines = text.split('\n')
        
        if len(lines) <= max_lines:
            return text
        
        # Show first and last parts
        first_part = '\n'.join(lines[:max_lines//2])
        last_part = '\n'.join(lines[-max_lines//2:])
        
        return f"{first_part}\n\n... [{len(lines) - max_lines} more lines] ...\n\n{last_part}"
    
    def _format_file_path(self, path: str) -> str:
        """Format file path for display."""
        if not path:
            return ""
        
        path_obj = Path(path)
        home = Path.home()
        
        # Try to make relative to home
        try:
            rel_path = path_obj.relative_to(home)
            return f"~/{rel_path}"
        except ValueError:
            pass
        
        # Return as-is but clean up
        return str(path_obj).replace("\\", "/")
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size for display."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
