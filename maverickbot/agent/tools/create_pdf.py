"""Create PDF tool - with automatic PDF reading support."""
import os
import unicodedata
from typing import Any, Dict, List, Union, Optional
from .base import Tool, ToolResult
from .read_pdf import ReadPdfTool


class CreatePdfTool(Tool):
    """Tool for creating PDF documents with automatic source PDF reading."""

    def __init__(self):
        super().__init__(
            name="create_pdf",
            description="""Create a PDF document. Automatically reads source PDFs if specified.
Input: {"source_pdf": "input.pdf", "output": "output.pdf"} - reads and creates new PDF
Input: {"content": "text", "output": "output.pdf"} - creates from text
Input: {"content_file": "file.txt", "output": "output.pdf"} - reads from text file
""",
        )
        self._read_pdf = ReadPdfTool()

    async def execute(self, **kwargs) -> ToolResult:
        try:
            content = kwargs.get("content", "")
            output = kwargs.get("output", "document.pdf")
            title = kwargs.get("title", "")
            source_pdf = kwargs.get("source_pdf", "")

            if source_pdf:
                if not os.path.exists(source_pdf):
                    return ToolResult(success=False, result=None, error=f"Source PDF not found: {source_pdf}")
                result = await self._read_pdf.execute(file=source_pdf)
                if result.success:
                    content = result.result
                else:
                    return ToolResult(success=False, result=None, error=f"Failed to read source PDF: {result.error}")
            
            content_file = kwargs.get("content_file", "")
            if content_file and not content:
                if os.path.exists(content_file):
                    with open(content_file, 'r', encoding='utf-8') as f:
                        content = f.read()
            
            if not content:
                return ToolResult(success=False, result=None, error="Content cannot be empty")
            
            if isinstance(content, str):
                content = content.strip()
                if content.startswith('"') and content.endswith('"'):
                    try:
                        import json
                        content = json.loads(content)
                    except:
                        pass
                if content.startswith('```'):
                    lines = content.split('\n')
                    content = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])
                content = content.replace('\\"', '"').replace('\\n', '\n')

            output = os.path.abspath(output)
            os.makedirs(os.path.dirname(output) or '.', exist_ok=True)

            # Try to find generate_pdf.js in multiple locations
            possible_paths = [
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'workspace', 'generate_pdf.js'),
                os.path.join(os.getcwd(), 'workspace', 'generate_pdf.js'),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'workspace', 'generate_pdf.js')
            ]
            
            html_gen_path = next((p for p in possible_paths if os.path.exists(p)), None)
            
            if html_gen_path:
                import asyncio
                temp_content_file = os.path.join(os.path.dirname(output), f'.temp_{os.path.basename(output)}.txt')
                try:
                    with open(temp_content_file, 'w', encoding='utf-8') as f:
                        if isinstance(content, list):
                            f.write('\n'.join(str(item) for item in content))
                        else:
                            f.write(str(content))
                    
                    title_arg = f'--title={title.replace(" ", "_")}' if title else ''
                    cmd = ['node', html_gen_path, output, f'--source={temp_content_file}']
                    if title_arg:
                        cmd.append(title_arg)
                    
                    # Use non-blocking async subprocess
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=60)
                    
                    if process.returncode == 0:
                        if os.path.exists(output):
                            return ToolResult(success=True, result=f"Created {output} using high-fidelity generator")
                    else:
                        logger.warning(f"HTML PDF generator failed: {stderr.decode()}")
                except Exception as e:
                    logger.warning(f"Error using HTML PDF generator: {e}")
                finally:
                    if os.path.exists(temp_content_file):
                        try:
                            os.unlink(temp_content_file)
                        except:
                            pass

            # Fallback to fpdf2
            from fpdf import FPDF
            
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            font_size = kwargs.get("font_size", 11)
            margins = kwargs.get("margins", 15)
            
            pdf.set_font("Arial", size=font_size)
            
            if title:
                pdf.set_font("Arial", "B", font_size + 4)
                pdf.cell(0, 10, title, ln=True, align="C")
                pdf.ln(5)
                pdf.set_font("Arial", size=font_size)
            
            if isinstance(content, list):
                for item in content:
                    self._add_content(pdf, self._safe_text(str(item)), font_size)
            else:
                self._add_content(pdf, self._safe_text(str(content)), font_size)
            
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
                pdf.multi_cell(0, 8, self._safe_text(line[2:]))
                pdf.ln(2)
                pdf.set_font("Arial", size=font_size)
            elif line.startswith('## ') or line.startswith('### '):
                pdf.set_font("Arial", "B", font_size + 3)
                prefix = line.find(' ') + 1
                pdf.multi_cell(0, 7, self._safe_text(line[prefix:]))
                pdf.ln(2)
                pdf.set_font("Arial", size=font_size)
            elif line.startswith('- ') or line.startswith('* '):
                pdf.set_font("Arial", size=font_size)
                pdf.multi_cell(5, 5, "-")
                pdf.multi_cell(0, 5, self._safe_text(line[2:]))
            elif '|' in line and line.count('|') > 1:
                self._add_table_row(pdf, line, font_size)
            else:
                pdf.multi_cell(0, 5, self._safe_text(line))
                pdf.ln(1)
        
        pdf.ln(3)

    def _add_table_row(self, pdf: "FPDF", line: str, font_size: int):
        """Add a table row."""
        cells = [c.strip() for c in line.split('|') if c.strip()]
        for cell in cells:
            pdf.cell(40, 5, self._safe_text(cell))
        pdf.ln()

    def _safe_text(self, text: str) -> str:
        """Normalize text to characters supported by core PDF fonts."""
        if not text:
            return ""
        # Normalize unicode (e.g., fancy quotes, arrows, bullets)
        normalized = unicodedata.normalize("NFKD", text)
        # Encode to latin-1 with replacement to avoid hard failures in core fonts
        safe = normalized.encode("latin-1", errors="replace").decode("latin-1")
        # Replace unreadable placeholders with simple ASCII fallbacks
        safe = safe.replace("?", "-") if text.count("?") == 0 and safe.count("?") > 5 else safe
        return safe

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source_pdf": {
                    "type": "string", 
                    "description": "Source PDF file to read and convert (auto-reads content)"
                },
                "content": {
                    "type": "string", 
                    "description": "Text content for PDF"
                },
                "content_file": {
                    "type": "string",
                    "description": "Read content from a text file"
                },
                "output": {"type": "string", "description": "Output filename"},
                "title": {"type": "string", "description": "Optional PDF title"},
                "font_size": {"type": "number", "description": "Font size (default: 11)", "default": 11},
                "margins": {"type": "number", "description": "Page margins (default: 15)", "default": 15}
            },
            "required": ["output"]
        }
