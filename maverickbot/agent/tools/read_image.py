"""Read image tool."""
from typing import Any, Dict
from .base import Tool, ToolResult


class ReadImageTool(Tool):
    """Tool for reading image information."""

    def __init__(self):
        super().__init__(
            name="read_image",
            description="Get information about an image file. Input: JSON with 'file' (path).",
        )

    async def execute(self, **kwargs) -> ToolResult:
        try:
            from PIL import Image
            
            file_path = kwargs.get("file", "")
            if not file_path:
                return ToolResult(success=False, result=None, error="No file specified")
            
            with Image.open(file_path) as img:
                info = f"Format: {img.format}\nSize: {img.size}\nMode: {img.mode}\nDimensions: {img.width}x{img.height}"
                
                if hasattr(img, 'info'):
                    info += f"\nInfo: {img.info}"
            
            return ToolResult(success=True, result=info)
        except ImportError:
            return ToolResult(success=False, result=None, error="Pillow not installed. Run: pip install Pillow")
        except FileNotFoundError:
            return ToolResult(success=False, result=None, error=f"File not found: {file_path}")
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file": {"type": "string", "description": "Path to the image file"}
            },
            "required": ["file"]
        }