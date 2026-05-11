"""Workspace tool for managing a dedicated workspace folder."""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from .base import Tool, ToolResult


class WorkspaceTool(Tool):
    """Tool for managing a dedicated workspace folder."""

    WORKSPACE_DIR = Path.home() / "maverickbot_workspace"

    def __init__(self):
        super().__init__(
            name="workspace",
            description="Manage workspace folder. Actions: init, list, cleanup. Use 'init' to create workspace.",
        )
        self._ensure_workspace()

    def _ensure_workspace(self):
        """Ensure workspace directory exists."""
        self.WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["init", "list", "cleanup", "info"],
                    "description": "Action to perform"
                },
                "path": {"type": "string", "description": "Path relative to workspace"},
                "subfolder": {"type": "string", "description": "Subfolder name for init"}
            },
            "required": ["action"]
        }

    async def execute(self, action: str, path: Optional[str] = None, subfolder: Optional[str] = None, **kwargs) -> ToolResult:
        try:
            if action == "init":
                return self._init_workspace(subfolder)
            elif action == "list":
                return self._list_workspace(path)
            elif action == "cleanup":
                return self._cleanup_workspace()
            elif action == "info":
                return self._workspace_info()
            else:
                return ToolResult(success=False, result=None, error=f"Unknown action: {action}")
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _init_workspace(self, subfolder: Optional[str] = None) -> ToolResult:
        """Initialize workspace folder."""
        if subfolder:
            target = self.WORKSPACE_DIR / subfolder
            target.mkdir(parents=True, exist_ok=True)
            return ToolResult(success=True, result=f"Created workspace subfolder: {target}")
        
        self.WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        return ToolResult(success=True, result=f"Workspace initialized at: {self.WORKSPACE_DIR}")

    def _list_workspace(self, path: Optional[str] = None) -> ToolResult:
        """List contents of workspace or subfolder."""
        target = self.WORKSPACE_DIR
        if path:
            target = target / path
        
        if not target.exists():
            return ToolResult(success=False, result=None, error=f"Path not found: {target}")
        
        items = []
        for item in target.iterdir():
            item_type = "folder" if item.is_dir() else "file"
            size = item.stat().st_size if item.is_file() else 0
            items.append(f"{item_type}: {item.name} ({size} bytes)")
        
        return ToolResult(success=True, result="\n".join(items) if items else "Empty")

    def _cleanup_workspace(self) -> ToolResult:
        """Remove all contents of workspace."""
        count = 0
        for item in self.WORKSPACE_DIR.iterdir():
            if item.is_dir():
                import shutil
                shutil.rmtree(item)
            else:
                item.unlink()
            count += 1
        return ToolResult(success=True, result=f"Cleaned {count} items from workspace")

    def _workspace_info(self) -> ToolResult:
        """Get workspace information."""
        if not self.WORKSPACE_DIR.exists():
            return ToolResult(success=True, result=f"Workspace not initialized. Use 'workspace init' to create.")
        
        total_files = sum(1 for f in self.WORKSPACE_DIR.rglob("*") if f.is_file())
        total_size = sum(f.stat().st_size for f in self.WORKSPACE_DIR.rglob("*") if f.is_file())
        
        return ToolResult(success=True, result=f"Location: {self.WORKSPACE_DIR}\nFiles: {total_files}\nSize: {total_size:,} bytes")


class WorkspaceCopyTool(Tool):
    """Copy files to workspace folder."""

    def __init__(self):
        super().__init__(
            name="workspace_copy",
            description="Copy a file to the workspace folder.",
        )

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Source file path"},
                "dest_name": {"type": "string", "description": "Destination name (optional)"}
            },
            "required": ["source"]
        }

    async def execute(self, source: str, dest_name: Optional[str] = None, **kwargs) -> ToolResult:
        try:
            import shutil
            source_path = Path(source)
            if not source_path.exists():
                return ToolResult(success=False, result=None, error=f"Source not found: {source}")
            
            workspace = Path.home() / "maverickbot_workspace"
            workspace.mkdir(parents=True, exist_ok=True)
            
            dest = workspace / (dest_name or source_path.name)
            shutil.copy2(source, dest)
            
            return ToolResult(success=True, result=f"Copied to: {dest}")
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))
