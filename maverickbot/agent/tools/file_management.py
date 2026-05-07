"""File management tools."""

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List
from .base import Tool, ToolResult


class DeleteFileTool(Tool):
    """Tool for deleting files."""

    def __init__(self):
        super().__init__(
            name="delete_file",
            description="Delete a file or directory.",
        )

    async def execute(self, path: str, recursive: bool = False, **kwargs) -> ToolResult:
        try:
            path_obj = Path(path)
            if not path_obj.exists():
                return ToolResult(success=False, result=None, error=f"Path not found: {path}")
            
            if path_obj.is_file():
                path_obj.unlink()
                return ToolResult(success=True, result=f"Deleted file: {path}")
            elif path_obj.is_dir():
                if recursive:
                    shutil.rmtree(path_obj)
                    return ToolResult(success=True, result=f"Deleted directory: {path}")
                else:
                    path_obj.rmdir()
                    return ToolResult(success=True, result=f"Deleted empty directory: {path}")
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The path to delete"},
                "recursive": {"type": "boolean", "description": "Delete directories recursively", "default": False},
            },
            "required": ["path"],
        }


class ListDirectoryTool(Tool):
    """Tool for listing directory contents."""

    def __init__(self):
        super().__init__(
            name="list_directory",
            description="List files and directories in a path.",
        )

    async def execute(self, path: str = ".", include_hidden: bool = False, **kwargs) -> ToolResult:
        try:
            path_obj = Path(path)
            if not path_obj.exists():
                return ToolResult(success=False, result=None, error=f"Path not found: {path}")
            if not path_obj.is_dir():
                return ToolResult(success=False, result=None, error=f"Not a directory: {path}")

            items = []
            for item in path_obj.iterdir():
                if not include_hidden and item.name.startswith("."):
                    continue
                items.append({
                    "name": item.name,
                    "type": "dir" if item.is_dir() else "file",
                })
            
            items.sort(key=lambda x: (x["type"] != "dir", x["name"]))
            return ToolResult(success=True, result=items)
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The directory to list", "default": "."},
                "include_hidden": {"type": "boolean", "description": "Include hidden files", "default": False},
            },
            "required": [],
        }


class CopyFileTool(Tool):
    """Tool for copying files and directories."""

    def __init__(self):
        super().__init__(
            name="copy_file",
            description="Copy a file or directory to a destination.",
        )

    async def execute(self, source: str, destination: str, overwrite: bool = False, **kwargs) -> ToolResult:
        try:
            src = Path(source)
            dst = Path(destination)
            
            if not src.exists():
                return ToolResult(success=False, result=None, error=f"Source not found: {source}")
            
            if dst.exists() and not overwrite:
                return ToolResult(success=False, result=None, error=f"Destination exists: {destination}")

            if src.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
                return ToolResult(success=True, result=f"Copied directory: {source} -> {destination}")
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                return ToolResult(success=True, result=f"Copied file: {source} -> {destination}")
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Source path"},
                "destination": {"type": "string", "description": "Destination path"},
                "overwrite": {"type": "boolean", "description": "Overwrite if exists", "default": False},
            },
            "required": ["source", "destination"],
        }


class MoveFileTool(Tool):
    """Tool for moving/renaming files and directories."""

    def __init__(self):
        super().__init__(
            name="move_file",
            description="Move or rename a file or directory.",
        )

    async def execute(self, source: str, destination: str, overwrite: bool = False, **kwargs) -> ToolResult:
        try:
            src = Path(source)
            dst = Path(destination)
            
            if not src.exists():
                return ToolResult(success=False, result=None, error=f"Source not found: {source}")
            
            if dst.exists() and not overwrite:
                return ToolResult(success=False, result=None, error=f"Destination exists: {destination}")
            
            if dst.exists():
                shutil.rmtree(dst)
            
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            return ToolResult(success=True, result=f"Moved: {source} -> {destination}")
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Source path"},
                "destination": {"type": "string", "description": "Destination path"},
                "overwrite": {"type": "boolean", "description": "Overwrite if exists", "default": False},
            },
            "required": ["source", "destination"],
        }


class CreateDirectoryTool(Tool):
    """Tool for creating directories."""

    def __init__(self):
        super().__init__(
            name="create_directory",
            description="Create a directory.",
        )

    async def execute(self, path: str, parents: bool = True, **kwargs) -> ToolResult:
        try:
            path_obj = Path(path)
            path_obj.mkdir(parents=parents, exist_ok=True)
            return ToolResult(success=True, result=f"Created directory: {path}")
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path to create"},
                "parents": {"type": "boolean", "description": "Create parent directories", "default": True},
            },
            "required": ["path"],
        }


class FileExistsTool(Tool):
    """Tool for checking if a file or directory exists."""

    def __init__(self):
        super().__init__(
            name="file_exists",
            description="Check if a file or directory exists.",
        )

    async def execute(self, path: str, **kwargs) -> ToolResult:
        try:
            path_obj = Path(path)
            if not path_obj.exists():
                return ToolResult(success=True, result={"exists": False, "path": path})
            
            return ToolResult(success=True, result={
                "exists": True,
                "path": path,
                "type": "directory" if path_obj.is_dir() else "file",
            })
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to check"},
            },
            "required": ["path"],
        }


class GetFileInfoTool(Tool):
    """Tool for getting file information."""

    def __init__(self):
        super().__init__(
            name="get_file_info",
            description="Get information about a file or directory.",
        )

    async def execute(self, path: str, **kwargs) -> ToolResult:
        try:
            path_obj = Path(path)
            if not path_obj.exists():
                return ToolResult(success=False, result=None, error=f"Path not found: {path}")
            
            stat = path_obj.stat()
            info = {
                "path": str(path_obj),
                "name": path_obj.name,
                "type": "directory" if path_obj.is_dir() else "file",
                "size": stat.st_size,
                "created": stat.st_ctime,
                "modified": stat.st_mtime,
                "accessed": stat.st_atime,
            }
            return ToolResult(success=True, result=info)
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to file or directory"},
            },
            "required": ["path"],
        }