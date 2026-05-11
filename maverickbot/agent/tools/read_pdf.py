"""Read PDF tool."""
from typing import Any, Dict
from .base import Tool, ToolResult


class ReadPdfTool(Tool):
    """Tool for reading and extracting text from PDF files."""

    def __init__(self):
        super().__init__(
            name="read_pdf",
            description="Extract text from a PDF file. Input: JSON with 'file' (path to PDF).",
        )

    async def execute(self, **kwargs) -> ToolResult:
        try:
            from pypdf import PdfReader
            
            file_path = kwargs.get("file", "")
            if not file_path:
                return ToolResult(success=False, result=None, error="No file specified")
            
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            
            limit = 32000
            truncated = len(text) > limit
            result_text = text[:limit]
            
            if truncated:
                result_text += f"\n\n[WARNING: Content truncated due to size. Only first {limit} characters shown.]"
            
            return ToolResult(success=True, result=result_text)
        except ImportError:
            return ToolResult(success=False, result=None, error="pypdf not installed. Run: pip install pypdf")
        except FileNotFoundError:
            return ToolResult(success=False, result=None, error=f"File not found: {file_path}")
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file": {"type": "string", "description": "Path to the PDF file"}
            },
            "required": ["file"]
        }