"""File finder for locating files from vague descriptions."""
import os
import re
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from .constants import COMMON_LOCATIONS, FILE_TYPES


@dataclass
class FileCandidate:
    """A possible file match."""
    path: Path
    name: str
    modified: datetime
    size: int
    match_score: float
    reason: str


class FileFinder:
    """Find files from partial/vague references."""
    
    def __init__(self):
        self.search_locations = [loc["path"] for loc in COMMON_LOCATIONS]
    
    def find(
        self, 
        hint: str = "", 
        file_type: str = None, 
        max_results: int = 5,
        search_recent: int = 7
    ) -> List[FileCandidate]:
        """
        Find files matching the given hint.
        
        Args:
            hint: Partial filename or description (e.g., "PDF from downloads")
            file_type: Type of file (pdf, document, image, etc.)
            max_results: Maximum number of results
            search_recent: Search only files modified in last N days (0 = all)
        
        Returns:
            List of FileCandidate sorted by relevance
        """
        candidates = []
        hint_lower = hint.lower()
        
        # Determine search paths
        search_paths = self._get_search_paths(hint_lower)
        
        # Get extensions to search
        extensions = self._get_extensions(file_type)
        
        # Search each location
        for base_path in search_paths:
            if not base_path.exists():
                continue
            
            for file_path in base_path.rglob("*"):
                if not file_path.is_file():
                    continue
                
                # Filter by extension
                if extensions and file_path.suffix.lower() not in extensions:
                    continue
                
                # Filter by recent modification
                if search_recent > 0:
                    try:
                        mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                        days_old = (datetime.now() - mod_time).days
                        if days_old > search_recent:
                            continue
                    except:
                        pass
                
                # Calculate match score
                score, reason = self._calculate_match_score(file_path, hint_lower, file_type)
                
                if score > 0:
                    candidates.append(FileCandidate(
                        path=file_path,
                        name=file_path.name,
                        modified=datetime.fromtimestamp(file_path.stat().st_mtime),
                        size=file_path.stat().st_size,
                        match_score=score,
                        reason=reason
                    ))
        
        # Sort by score (descending) and return top results
        candidates.sort(key=lambda x: x.match_score, reverse=True)
        return candidates[:max_results]
    
    def find_by_name(self, name_hint: str, file_type: str = None, max_results: int = 5) -> List[FileCandidate]:
        """Find files by partial name match."""
        return self.find(hint=name_hint, file_type=file_type, max_results=max_results, search_recent=0)
    
    def find_recent(self, file_type: str = None, max_results: int = 5) -> List[FileCandidate]:
        """Find recently modified files."""
        return self.find(hint="", file_type=file_type, max_results=max_results, search_recent=7)
    
    def find_in_directory(self, directory: Path, file_type: str = None, max_results: int = 5) -> List[FileCandidate]:
        """Find files in a specific directory."""
        candidates = []
        extensions = self._get_extensions(file_type)
        
        if not directory.exists():
            return candidates
        
        for file_path in directory.rglob("*"):
            if not file_path.is_file():
                continue
            
            if extensions and file_path.suffix.lower() not in extensions:
                continue
            
            try:
                candidates.append(FileCandidate(
                    path=file_path,
                    name=file_path.name,
                    modified=datetime.fromtimestamp(file_path.stat().st_mtime),
                    size=file_path.stat().st_size,
                    match_score=1.0,
                    reason="Exact directory match"
                ))
            except:
                pass
        
        candidates.sort(key=lambda x: x.modified, reverse=True)
        return candidates[:max_results]
    
    def _get_search_paths(self, hint_lower: str) -> List[Path]:
        """Determine which directories to search based on hint."""
        paths = []
        
        if "downloads" in hint_lower or not hint_lower:
            paths.append(Path.home() / "Downloads")
        if "desktop" in hint_lower or not hint_lower:
            paths.append(Path.home() / "Desktop")
        if "documents" in hint_lower or not hint_lower:
            paths.append(Path.home() / "Documents")
        if "pictures" in hint_lower or not hint_lower:
            paths.append(Path.home() / "Pictures")
        
        # If nothing specified, search all common locations
        if not paths:
            paths = self.search_locations
        
        return list(set(paths))  # Remove duplicates
    
    def _get_extensions(self, file_type: str) -> List[str]:
        """Get file extensions for a file type."""
        if not file_type:
            return []
        return FILE_TYPES.get(file_type.lower(), [])
    
    def _calculate_match_score(self, path: Path, hint: str, file_type: str) -> Tuple[float, str]:
        """Calculate how well a file matches the hint."""
        name_lower = path.name.lower()
        
        # Exact name match (highest score)
        if hint and name_lower == hint:
            return 1.0, "Exact name match"
        
        # Filename contains hint
        if hint and hint in name_lower:
            # Higher score for match at beginning
            if name_lower.startswith(hint):
                return 0.9, "Match at filename start"
            return 0.7, "Filename contains hint"
        
        # Extract potential filename from hint
        if hint:
            hint_parts = hint.split()
            for part in hint_parts:
                if len(part) > 2 and part in name_lower:
                    return 0.6, f"Contains '{part}'"
        
        # File type match (no hint)
        if file_type and not hint:
            extensions = self._get_extensions(file_type)
            if path.suffix.lower() in extensions:
                return 0.5, f"{file_type} file"
        
        return 0.0, ""
    
    def format_candidates_for_ui(self, candidates: List[FileCandidate]) -> str:
        """Format candidates for user-friendly display."""
        if not candidates:
            return "I couldn't find any matching files."
        
        lines = []
        for i, candidate in enumerate(candidates, 1):
            size_str = self._format_size(candidate.size)
            days_ago = self._days_ago(candidate.modified)
            lines.append(f"  {i}. {candidate.name}")
            lines.append(f"     {size_str} • {days_ago} • in {candidate.path.parent.name}")
        
        return "\n".join(lines)
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size for display."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
    
    def _days_ago(self, dt: datetime) -> str:
        """Format days ago for display."""
        days = (datetime.now() - dt).days
        if days == 0:
            return "today"
        elif days == 1:
            return "yesterday"
        elif days < 7:
            return f"{days} days ago"
        elif days < 30:
            weeks = days // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        else:
            months = days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
