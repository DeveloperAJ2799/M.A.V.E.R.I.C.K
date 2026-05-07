"""Read DOCX tool."""
from typing import Any, Dict
from .base import Tool, ToolResult


class ReadDocxTool(Tool):
    """Tool for reading Word documents."""

    def __init__(self):
        super().__init__(
            name="read_docx",
            description="Read and extract text from a Word DOCX file. Input: JSON with 'file' (path).",
        )

    async def execute(self, **kwargs) -> ToolResult:
        try:
            from docx import Document
            
            file_path = kwargs.get("file", "")
            if not file_path:
                return ToolResult(success=False, result=None, error="No file specified")
            
            doc = Document(file_path)
            text = ""
            for para in doc.paragraphs:
                text += para.text + "\n"
            
            return ToolResult(success=True, result=text[:8000])
        except ImportError:
            return ToolResult(success=False, result=None, error="python-docx not installed. Run: pip install python-docx")
        except FileNotFoundError:
            return ToolResult(success=False, result=None, error=f"File not found: {file_path}")
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file": {"type": "string", "description": "Path to the DOCX file"}
            },
            "required": ["file"]
        }