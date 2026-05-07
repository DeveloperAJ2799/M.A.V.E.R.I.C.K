"""Create PDF tool."""
import os
from typing import Any, Dict, List, Union
from .base import Tool, ToolResult


class CreatePdfTool(Tool):
    """Tool for creating PDF documents with customizable formatting."""

    def __init__(self):
        super().__init__(
            name="create_pdf",
            description="""Create a PDF document. RECOMMENDED APPROACH: 
1. First write full content to a .txt file using write_file tool
2. Then call create_pdf with content_file parameter pointing to that file
Alternatively pass content directly, but ensure ALL text is included.""",
        )

    async def execute(self, **kwargs) -> ToolResult:
        try:
            from fpdf import FPDF
            
            content = kwargs.get("content", "")
            output = kwargs.get("output", "document.pdf")
            title = kwargs.get("title", "")
            font_size = kwargs.get("font_size", 11)
            margins = kwargs.get("margins", 15)
            
            # Support reading from file
            content_file = kwargs.get("content_file", "")
            if content_file and os.path.exists(content_file):
                with open(content_file, 'r', encoding='utf-8') as f:
                    content = f.read()
            
            if not content:
                return ToolResult(success=False, result=None, error="Content cannot be empty")
            
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=margins)
            
            pdf.set_font("Arial", size=font_size)
            
            if title:
                pdf.set_font("Arial", "B", font_size + 4)
                pdf.cell(0, 10, title, ln=True, align="C")
                pdf.ln(5)
                pdf.set_font("Arial", size=font_size)
            
            if isinstance(content, list):
                for item in content:
                    self._add_content(pdf, str(item), font_size)
            else:
                self._add_content(pdf, str(content), font_size)
            
            output_dir = os.path.dirname(output)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            pdf.output(output)
            return ToolResult(success=True, result=f"Created {output} ({pdf.page_no()} pages)")
        except ImportError:
            return ToolResult(success=False, result=None, error="fpdf2 not installed. Run: pip install fpdf2")
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _add_content(self, pdf: "FPDF", text: str, font_size: int):
        """Add content to PDF with proper formatting."""
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                pdf.ln(3)
                continue
            
            if line.startswith('# '):
                pdf.set_font("Arial", "B", font_size + 6)
                pdf.multi_cell(0, 8, line[2:])
                pdf.ln(2)
                pdf.set_font("Arial", size=font_size)
            elif line.startswith('## ') or line.startswith('### '):
                pdf.set_font("Arial", "B", font_size + 3)
                prefix = line.find(' ') + 1
                pdf.multi_cell(0, 7, line[prefix:])
                pdf.ln(2)
                pdf.set_font("Arial", size=font_size)
            elif line.startswith('- ') or line.startswith('* '):
                pdf.set_font("Arial", size=font_size)
                pdf.multi_cell(5, 5, "•")
                pdf.multi_cell(0, 5, line[2:])
            elif '|' in line and line.count('|') > 1:
                self._add_table_row(pdf, line, font_size)
            else:
                pdf.multi_cell(0, 5, line)
                pdf.ln(1)
        
        pdf.ln(3)

    def _add_table_row(self, pdf: "FPDF", line: str, font_size: int):
        """Add a table row."""
        cells = [c.strip() for c in line.split('|') if c.strip()]
        for cell in cells:
            pdf.cell(40, 5, cell)
        pdf.ln()

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string", 
                    "description": "Full text content for PDF. Include ALL content - do not truncate."
                },
                "content_file": {
                    "type": "string",
                    "description": "Alternative: Read content from a text file path"
                },
                "output": {"type": "string", "description": "Output filename"},
                "title": {"type": "string", "description": "Optional PDF title"},
                "font_size": {"type": "number", "description": "Font size (default: 11)", "default": 11},
                "margins": {"type": "number", "description": "Page margins (default: 15)", "default": 15}
            },
            "required": ["content"]
        }