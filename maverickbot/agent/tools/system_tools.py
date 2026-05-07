"""System integration tools."""
import asyncio
import subprocess
import platform
import psutil
import os
from typing import Any, Dict
from .base import Tool, ToolResult


class SystemInfoTool(Tool):
    """Tool for getting system information."""

    def __init__(self):
        super().__init__(
            name="system_info",
            description="Get system information (CPU, RAM, disk, OS). Input: JSON with optional 'detail' (basic/full).",
        )

    async def execute(self, **kwargs) -> ToolResult:
        detail = kwargs.get("detail", "basic")
        
        try:
            info = []
            
            # OS Info
            info.append(f"OS: {platform.system()} {platform.release()}")
            info.append(f"Python: {platform.python_version()}")
            
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            info.append(f"CPU: {cpu_percent}% ({cpu_count} cores)")
            
            # Memory
            mem = psutil.virtual_memory()
            info.append(f"RAM: {mem.percent}% used ({mem.used // (1024**2)}MB / {mem.total // (1024**2)}MB)")
            
            # Disk
            disk = psutil.disk_usage('/')
            info.append(f"Disk: {disk.percent}% used ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)")
            
            # Current directory
            info.append(f"CWD: {os.getcwd()}")
            
            if detail == "full":
                # More details
                info.append(f"\n--- Extended Info ---")
                info.append(f"Hostname: {platform.node()}")
                info.append(f"CPU Frequency: {psutil.cpu_freq().current if psutil.cpu_freq() else 'N/A'} MHz")
                info.append(f"Memory Available: {mem.available // (1024**2)}MB")
                
                # Network
                net = psutil.net_io_counters()
                info.append(f"Network: {net.bytes_sent // (1024**2)}MB sent, {net.bytes_recv // (1024**2)}MB received")
            
            return ToolResult(success=True, result="\n".join(info))
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "detail": {"type": "string", "description": "Detail level: 'basic' or 'full'"}
            }
        }


class ClipboardReadTool(Tool):
    """Tool for reading clipboard."""

    def __init__(self):
        super().__init__(
            name="clipboard_read",
            description="Read current clipboard content.",
        )

    async def execute(self, **kwargs) -> ToolResult:
        try:
            if platform.system() == "Windows":
                result = await asyncio.create_subprocess_shell(
                    "powershell -Command Get-Clipboard",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await result.communicate()
                content = stdout.decode('utf-8', errors='replace').strip()
            else:
                # macOS/Linux
                result = await asyncio.create_subprocess_shell(
                    "pbpaste" if platform.system() == "Darwin" else "xclip -selection clipboard -o",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await result.communicate()
                content = stdout.decode('utf-8', errors='replace').strip()
            
            if not content:
                content = "[Clipboard is empty]"
            elif len(content) > 5000:
                content = content[:5000] + "\n... (truncated)"
            
            return ToolResult(success=True, result=content)
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}}


class ClipboardWriteTool(Tool):
    """Tool for writing to clipboard."""

    def __init__(self):
        super().__init__(
            name="clipboard_write",
            description="Write text to clipboard. Input: JSON with 'text'.",
        )

    async def execute(self, **kwargs) -> ToolResult:
        text = kwargs.get("text", "")
        
        if not text:
            return ToolResult(success=False, result=None, error="No text provided")
        
        try:
            if platform.system() == "Windows":
                # Use PowerShell for Windows clipboard
                escaped_text = text.replace("'", "''").replace('"', '`"')
                proc = await asyncio.create_subprocess_exec(
                    "powershell", "-Command", f"Set-Clipboard -Value '{escaped_text}'",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            else:
                # macOS/Linux
                cmd = "pbcopy" if platform.system() == "Darwin" else f"echo -n '{text}' | xclip -selection clipboard"
                proc = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            
            await proc.communicate()
            return ToolResult(success=True, result="Text copied to clipboard")
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to copy to clipboard"}
            },
            "required": ["text"]
        }


class NotifyTool(Tool):
    """Tool for system notifications."""

    def __init__(self):
        super().__init__(
            name="notify",
            description="Send system notification. Input: JSON with 'message' and optional 'title'.",
        )

    async def execute(self, **kwargs) -> ToolResult:
        message = kwargs.get("message", "")
        title = kwargs.get("title", "M.A.V.E.R.I.C.K")
        
        if not message:
            return ToolResult(success=False, result=None, error="No message provided")
        
        try:
            system = platform.system()
            
            if system == "Windows":
                # Simple notification via PowerShell
                proc = await asyncio.create_subprocess_exec(
                    "powershell", "-Command", 
                    f'Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show("{message}", "{title}")',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            elif system == "Darwin":
                cmd = f'osascript -e \'display notification "{message}" with title "{title}"\''
                proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            else:
                cmd = f'notify-send "{title}" "{message}"'
                proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            
            await proc.communicate()
            return ToolResult(success=True, result="Notification sent")
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Notification message"},
                "title": {"type": "string", "description": "Notification title (default: M.A.V.E.R.I.C.K)"}
            },
            "required": ["message"]
        }