"""PDF to PDF tool - Read a PDF, expand content, create new PDF."""
import os
from typing import Any, Dict, Optional
from .base import Tool, ToolResult
from .read_pdf import ReadPdfTool
from .create_pdf import CreatePdfTool


class PdfToPdfTool(Tool):
    """Tool for reading a PDF, expanding its content, and creating a new PDF."""

    def __init__(self):
        super().__init__(
            name="pdf_to_pdf",
            description="""Read a PDF file, expand/enhance its content, and create a new PDF.
Use this to expand documents with more detailed information.
Input: {"source": "input.pdf", "output": "output.pdf", "instructions": "Expand on the topics with more detail"}""",
        )

    async def execute(self, **kwargs) -> ToolResult:
        try:
            source = kwargs.get("source", "")
            output = kwargs.get("output", "expanded.pdf")
            instructions = kwargs.get("instructions", "Expand and enhance the content")
            
            if not source:
                return ToolResult(success=False, result=None, error="Source PDF path required")
            
            # Read the source PDF
            read_tool = ReadPdfTool()
            result = await read_tool.execute(file=source)
            
            if not result.success:
                return ToolResult(success=False, result=None, error=f"Failed to read PDF: {result.error}")
            
            original_content = result.result
            
            # Return the content to the LLM so it can expand it
            return ToolResult(
                success=True, 
                result=f"""EXTRACTED CONTENT FROM {source}:
---
{original_content}
---
The above is the content of the source PDF. 
Your task: 
1. Expand and enhance this content based on the user's instructions: "{instructions}"
2. Use the 'create_pdf' tool to save the new expanded version to "{output}".
Provide a high-quality, detailed expansion."""
            )
            
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Source PDF file path to read"},
                "output": {"type": "string", "description": "Output PDF filename", "default": "expanded.pdf"},
                "instructions": {"type": "string", "description": "Instructions for expansion", "default": "Expand and enhance content"}
            },
            "required": ["source"]
        }


class QuickPdfTool(Tool):
    """Quick tool to read PDF and save content to text file for editing."""

    def __init__(self):
        super().__init__(
            name="pdf_extract",
            description="Extract text from PDF and save to a text file for editing.",
        )

    async def execute(self, **kwargs) -> ToolResult:
        try:
            source = kwargs.get("source", "")
            output = kwargs.get("output", "")
            
            if not source:
                return ToolResult(success=False, result=None, error="Source PDF path required")
            
            # Read the source PDF
            read_tool = ReadPdfTool()
            result = await read_tool.execute(file=source)
            
            if not result.success:
                return ToolResult(success=False, result=None, error=f"Failed to read PDF: {result.error}")
            
            content = result.result
            
            # Determine output file
            if not output:
                base = os.path.splitext(os.path.basename(source))[0]
                output = f"{base}_content.txt"
            
            # Write to file
            with open(output, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return ToolResult(
                success=True, 
                result=f"Extracted {len(content)} characters to {output}. Edit this file, then use create_pdf content_file: '{output}' output: 'new_document.pdf'"
            )
            
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Source PDF file path"},
                "output": {"type": "string", "description": "Output text filename (optional)"}
            },
            "required": ["source"]
        }