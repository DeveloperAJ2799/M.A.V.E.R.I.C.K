"""Execute Python code tool."""
import asyncio
import subprocess
import tempfile
import os
import shutil
from typing import Any, Dict
from pathlib import Path
from .base import Tool, ToolResult


class ExecuteCodeTool(Tool):
    """Tool for executing Python code safely."""

    def __init__(self):
        super().__init__(
            name="execute_code",
            description="Execute Python code and return output. Input: JSON with 'code' and optional 'timeout' (default 30s).",
        )
        self.max_timeout = 60  # max 60 seconds
        self.default_timeout = 30

    async def execute(self, **kwargs) -> ToolResult:
        code = kwargs.get("code", "")
        timeout_val = kwargs.get("timeout", self.default_timeout)
        try:
            timeout = int(timeout_val) if timeout_val else self.default_timeout
        except (ValueError, TypeError):
            timeout = self.default_timeout
        timeout = min(timeout, self.max_timeout)
        
        if not code:
            return ToolResult(success=False, result=None, error="No code provided")
        
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    'python', temp_file,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                ),
                timeout=timeout
            )
            
            stdout, stderr = await result.communicate()
            
            output = ""
            if stdout:
                output += stdout.decode('utf-8', errors='replace')
            if stderr:
                output += "\n[Errors]:\n" + stderr.decode('utf-8', errors='replace')
            
            if not output:
                output = "[No output]"
            
            # Truncate if too long
            if len(output) > 10000:
                output = output[:10000] + "\n... (output truncated)"
            
            if result.returncode == 0:
                return ToolResult(success=True, result=output)
            else:
                return ToolResult(success=False, result=output, error=f"Exit code: {result.returncode}")
                
        except asyncio.TimeoutError:
            return ToolResult(success=False, result=None, error=f"Execution timed out after {timeout}s")
        except FileNotFoundError:
            return ToolResult(success=False, result=None, error="Python not found. Ensure Python is installed.")
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))
        finally:
            # Cleanup temp file
            try:
                os.unlink(temp_file)
            except:
                pass

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default 30, max 60)"}
            },
            "required": ["code"]
        }