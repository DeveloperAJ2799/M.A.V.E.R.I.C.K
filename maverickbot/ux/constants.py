"""Constants for UX package - common locations and file types."""
from pathlib import Path
from typing import List, Dict

# Common user-accessible directories
COMMON_LOCATIONS = [
    {"name": "Downloads", "path": Path.home() / "Downloads"},
    {"name": "Desktop", "path": Path.home() / "Desktop"},
    {"name": "Documents", "path": Path.home() / "Documents"},
    {"name": "Pictures", "path": Path.home() / "Pictures"},
]

# File type mappings
FILE_TYPES = {
    "pdf": [".pdf"],
    "document": [".pdf", ".docx", ".doc", ".txt", ".rtf"],
    "spreadsheet": [".xlsx", ".xls", ".csv"],
    "presentation": [".pptx", ".ppt"],
    "image": [".png", ".jpg", ".jpeg", ".gif", ".bmp"],
    "code": [".py", ".js", ".html", ".css", ".json"],
    "video": [".mp4", ".avi", ".mov", ".mkv"],
    "audio": [".mp3", ".wav", ".flac", ".m4a"],
}

# Action verbs mapping
ACTION_VERBS = {
    "create": ["make", "create", "generate", "build", "produce", "new"],
    "read": ["read", "open", "look", "view", "show", "display", "check"],
    "edit": ["edit", "modify", "change", "update", "fix", "alter"],
    "delete": ["delete", "remove", "clear", "erase"],
    "copy": ["copy", "duplicate", "clone"],
    "expand": ["expand", "improve", "enhance", "extend", "elaborate", "detailed", "more"],
    "convert": ["convert", "transform", "export", "change to"],
    "search": ["search", "find", "look for", "grep"],
}

# Simple language mapping (technical → simple)
SIMPLE_LANGUAGE = {
    "tool": "feature",
    "execute": "run",
    "workflow": "steps",
    "invoke": "use",
    "parameter": "option",
    "schema": "format",
    "error": "problem",
    "success": "done",
    "output": "result",
    "document": "file",
    "content": "text",
    "directory": "folder",
}

# Confirmation messages
CONFIRM_MESSAGES = {
    "read_file": "I want to read this file for you: {path}",
    "create_file": "I'll create a new file here: {path}",
    "expand_pdf": "I'll expand this PDF and create a new one: {source} → {dest}",
    "delete_file": "I'm about to delete this file: {path}. This cannot be undone!",
    "run_command": "I'm about to run this command: {command}",
}
