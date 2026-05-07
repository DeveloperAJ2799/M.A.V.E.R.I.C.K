"""Create image tool."""
from typing import Any, Dict
from .base import Tool, ToolResult


class CreateImageTool(Tool):
    """Tool for creating simple images."""

    def __init__(self):
        super().__init__(
            name="create_image",
            description="Create a simple image. Input: JSON with 'text' (text to render), 'output' (filename), 'size' (WxH), 'color' (background).",
        )

    async def execute(self, **kwargs) -> ToolResult:
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            text = kwargs.get("text", "Hello")
            output = kwargs.get("output", "image.png")
            size = kwargs.get("size", (400, 200))
            bg_color = kwargs.get("color", "white")
            
            if isinstance(size, str):
                w, h = map(int, size.split('x'))
                size = (w, h)
            
            img = Image.new('RGB', size, color=bg_color)
            draw = ImageDraw.Draw(img)
            
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except:
                font = ImageFont.load_default()
            
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            position = ((size[0] - text_width) // 2, (size[1] - text_height) // 2)
            
            draw.text(position, text, fill="black", font=font)
            img.save(output)
            
            return ToolResult(success=True, result=f"Created {output}")
        except ImportError:
            return ToolResult(success=False, result=None, error="Pillow not installed. Run: pip install Pillow")
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to render as image"},
                "output": {"type": "string", "description": "Output filename (default: image.png)"},
                "size": {"type": "string", "description": "Image size as WxH (e.g., 400x200)"},
                "color": {"type": "string", "description": "Background color name"}
            },
            "required": ["text"]
        }