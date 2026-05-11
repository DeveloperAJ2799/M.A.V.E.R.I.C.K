"""Confirmation UI for friendly action verification."""
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

from .file_finder import FileFinder, FileCandidate
from .constants import CONFIRM_MESSAGES


class ConfirmationResult(Enum):
    CONFIRMED = "confirmed"
    DENIED = "denied"
    CHANGED = "changed"
    CANCELLED = "cancelled"


@dataclass
class ConfirmationContext:
    """Context for a confirmation request."""
    action: str
    description: str
    source_path: Optional[str] = None
    target_path: Optional[str] = None
    file_candidates: List[FileCandidate] = None
    extra_info: Dict[str, Any] = None


class ConfirmationUI:
    """User-friendly confirmation interface."""
    
    def __init__(self):
        self.file_finder = FileFinder()
        self.pending_confirmation: Optional[ConfirmationContext] = None
    
    def build_confirmation_message(self, context: ConfirmationContext) -> str:
        """Build a user-friendly confirmation message."""
        lines = []
        
        # Main description
        lines.append(context.description)
        lines.append("")
        
        # Source file
        if context.source_path:
            lines.append(f"  From: {self._format_path(context.source_path)}")
        
        # Target file
        if context.target_path:
            lines.append(f"  To: {self._format_path(context.target_path)}")
        
        # Extra info
        if context.extra_info:
            for key, value in context.extra_info.items():
                lines.append(f"  {key}: {value}")
        
        lines.append("")
        lines.append("Is this okay? (yes/no)")
        
        return "\n".join(lines)
    
    def build_file_selection_message(
        self, 
        hint: str, 
        action: str, 
        file_type: str = "pdf"
    ) -> str:
        """Build message for file selection when path is unclear."""
        candidates = self.file_finder.find(hint=hint, file_type=file_type, max_results=5)
        
        lines = []
        lines.append(f"I'm not sure which {file_type.upper()} you mean.")
        
        if candidates:
            lines.append("")
            lines.append(f"Here are some recent {file_type.upper()} files I found:")
            lines.append("")
            lines.append(self.file_finder.format_candidates_for_ui(candidates))
            lines.append("")
            lines.append("Which one did you mean? (type the number or name)")
        else:
            lines.append("")
            lines.append(f"I couldn't find any {file_type.upper()} files in your common folders.")
            lines.append("")
            lines.append("Try:")
            lines.append("  • Drag the file into this window")
            lines.append("  • Or type the full path (e.g., C:\\Folder\\file.pdf)")
        
        return "\n".join(lines)
    
    def parse_user_response(self, response: str, candidates: List[FileCandidate] = None) -> ConfirmationResult:
        """Parse user's response to confirmation."""
        response = response.strip().lower()
        
        # Handle yes/no variants
        yes_words = ["yes", "y", "yeah", "yep", "sure", "okay", "ok", "do it", "go ahead", "1"]
        no_words = ["no", "n", "nope", "nah", "cancel", "don't", "stop", "2"]
        change_words = ["change", "different", "other", "another"]
        
        if any(response.startswith(word) for word in yes_words):
            return ConfirmationResult.CONFIRMED
        
        if any(response.startswith(word) for word in no_words):
            return ConfirmationResult.DENIED
        
        if any(word in response for word in change_words):
            return ConfirmationResult.CHANGED
        
        # Check if response is a number for file selection
        if candidates:
            try:
                idx = int(response) - 1
                if 0 <= idx < len(candidates):
                    self.selected_candidate = candidates[idx]
                    return ConfirmationResult.CONFIRMED
            except ValueError:
                pass
            
            # Check if response matches a filename
            for i, candidate in enumerate(candidates):
                if candidate.name.lower() in response or response in candidate.name.lower():
                    self.selected_candidate = candidate
                    return ConfirmationResult.CONFIRMED
        
        return ConfirmationResult.DENIED
    
    def get_selected_file_path(self) -> Optional[str]:
        """Get the path of the file selected by user."""
        if hasattr(self, 'selected_candidate'):
            return str(self.selected_candidate.path)
        return None
    
    def _format_path(self, path: str) -> str:
        """Format path for display - use short form for readability."""
        if not path:
            return ""
        
        path_obj = Path(path)
        home = Path.home()
        
        try:
            rel_path = path_obj.relative_to(home)
            return f"~/{rel_path}".replace("\\", "/")
        except ValueError:
            pass
        
        return str(path_obj).replace("\\", "/")
    
    def create_context(
        self,
        action: str,
        source_path: Optional[str] = None,
        target_path: Optional[str] = None,
        **kwargs
    ) -> ConfirmationContext:
        """Create a confirmation context."""
        description = kwargs.get("description", f"I'll {action} for you.")
        
        return ConfirmationContext(
            action=action,
            description=description,
            source_path=source_path,
            target_path=target_path,
            extra_info=kwargs
        )
