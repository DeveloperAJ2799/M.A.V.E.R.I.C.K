"""Universal data reading, writing, and conversion tools."""
import json
import csv
import io
import os
import re
from typing import Any, Dict, List, Union
from xml.etree import ElementTree as ET

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    import tomli as toml
    HAS_TOML = True
except ImportError:
    try:
        import toml as toml
        HAS_TOML = True
    except ImportError:
        HAS_TOML = False

from .base import Tool, ToolResult


class UniversalReadTool(Tool):
    """Read and parse any data file format - auto-detects format."""

    def __init__(self):
        super().__init__(
            name="universal_read",
            description="""Read and parse any data file. Auto-detects format.
Input: {"file": "path/to/file"}
Supported formats: JSON, YAML, TOML, XML, CSV, TSV, HTML, Markdown, Plain text""",
        )

    async def execute(self, file: str = "", content: str = "", **kwargs) -> ToolResult:
        try:
            if file:
                if not os.path.exists(file):
                    return ToolResult(success=False, result=None, error=f"File not found: {file}")
                with open(file, 'r', encoding='utf-8') as f:
                    raw_content = f.read()
                format_detected = self._detect_format(file, raw_content)
            elif content:
                raw_content = content
                format_detected = self._detect_format(None, content)
            else:
                return ToolResult(success=False, result=None, error="No file or content provided")

            data = self._parse_content(raw_content, format_detected)

            if isinstance(data, (dict, list)):
                result = json.dumps(data, indent=2, ensure_ascii=False)
            else:
                result = str(data)

            if len(result) > 10000:
                result = result[:10000] + f"\n\n... (truncated, total: {len(result)} chars)"

            return ToolResult(success=True, result=f"[Format: {format_detected}]\n\n{result}")
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _detect_format(self, file: str = None, content: str = "") -> str:
        if file:
            ext = os.path.splitext(file)[1].lower()
            format_map = {
                '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml', '.toml': 'toml',
                '.xml': 'xml', '.csv': 'csv', '.tsv': 'tsv',
                '.html': 'html', '.htm': 'html', '.md': 'markdown', '.txt': 'text',
            }
            if ext in format_map:
                return format_map[ext]

        content_stripped = content.strip()

        if content_stripped.startswith('{') or content_stripped.startswith('['):
            return 'json'
        if content_stripped.startswith('<'):
            if any(tag in content_stripped.lower() for tag in ['<html', '<body', '<head', '<div', '<table']):
                return 'html'
            return 'xml'
        if HAS_YAML and (content_stripped.startswith('---') or ': ' in content_stripped[:200]):
            return 'yaml'
        if HAS_TOML and '[' in content_stripped[:3] and '=' in content_stripped:
            return 'toml'
        if ',' in content_stripped[:500] and '\n' in content_stripped:
            return 'csv'
        if '\t' in content_stripped[:500] and '\n' in content_stripped:
            return 'tsv'
        if content_stripped.startswith('#') or content_stripped.startswith('---'):
            return 'markdown'
        return 'text'

    def _parse_content(self, content: str, format_type: str) -> Any:
        content = content.strip()
        if format_type == 'json':
            return json.loads(content)
        elif format_type == 'yaml':
            if HAS_YAML:
                return yaml.safe_load(content)
            raise ImportError("PyYAML not installed. Run: pip install pyyaml")
        elif format_type == 'toml':
            if HAS_TOML:
                return toml.loads(content)
            raise ImportError("tomli not installed. Run: pip install tomli")
        elif format_type == 'xml':
            return self._xml_to_dict(ET.fromstring(content))
        elif format_type == 'csv':
            return list(csv.DictReader(io.StringIO(content)))
        elif format_type == 'tsv':
            return list(csv.DictReader(io.StringIO(content), delimiter='\t'))
        elif format_type == 'html':
            return self._html_to_dict(content)
        elif format_type == 'markdown':
            return {"type": "markdown", "content": content}
        else:
            return {"type": "text", "content": content}

    def _xml_to_dict(self, element) -> Dict:
        result = {}
        if element.attrib:
            result['@attributes'] = element.attrib
        if element.text and element.text.strip():
            if len(element) == 0:
                return element.text.strip()
            result['#text'] = element.text.strip()
        for child in element:
            child_data = self._xml_to_dict(child)
            if child.tag in result:
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data
        return result

    def _html_to_dict(self, content: str) -> Dict:
        import re as _re
        cleaned = _re.sub(r'<!--.*?-->', '', content, flags=_re.DOTALL)
        cleaned = _re.sub(r'<!DOCTYPE.*?>', '', cleaned, flags=_re.IGNORECASE)
        try:
            root = ET.fromstring(f"<root>{cleaned}</root>")
            return self._xml_to_dict(root)
        except:
            return {"type": "html", "content": content[:500]}

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file": {"type": "string", "description": "Path to the file to read"},
                "content": {"type": "string", "description": "Content string to parse instead of file"}
            }
        }


class ConvertDataTool(Tool):
    """Convert data between formats: JSON, YAML, TOML, CSV, XML, text."""

    def __init__(self):
        super().__init__(
            name="convert_data",
            description="""Convert data between formats.
Input: {"data": "...", "from_format": "json", "to_format": "yaml"}
Or: {"file": "input.json", "to_format": "yaml", "output": "output.yaml"}
Formats: json, yaml, toml, csv, xml, text""",
        )

    async def execute(self, data: str = "", file: str = "", from_format: str = "",
                      to_format: str = "", output: str = "", **kwargs) -> ToolResult:
        try:
            parsed = None
            if file:
                if not os.path.exists(file):
                    return ToolResult(success=False, result=None, error=f"File not found: {file}")
                with open(file, 'r', encoding='utf-8') as f:
                    raw = f.read()
                from_format = from_format or self._detect_from_file(file)
                parsed = self._parse_input(raw, from_format)
            elif data:
                parsed = self._parse_input(data, from_format or "json")
            else:
                return ToolResult(success=False, result=None, error="No data or file provided")

            result = self._format_output(parsed, to_format)
            if output:
                os.makedirs(os.path.dirname(output) or '.', exist_ok=True)
                with open(output, 'w', encoding='utf-8') as f:
                    f.write(result)
                return ToolResult(success=True, result=f"Saved to {output}")
            return ToolResult(success=True, result=result)
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _detect_from_file(self, file: str) -> str:
        ext = os.path.splitext(file)[1].lower()
        m = {'.json': 'json', '.yaml': 'yaml', '.yml': 'yaml', '.toml': 'toml',
             '.csv': 'csv', '.xml': 'xml', '.txt': 'text'}
        return m.get(ext, 'text')

    def _parse_input(self, content: str, fmt: str) -> Any:
        content = content.strip()
        if fmt == "json":
            return json.loads(content)
        elif fmt == "yaml" and HAS_YAML:
            return yaml.safe_load(content)
        elif fmt == "toml" and HAS_TOML:
            return toml.loads(content)
        elif fmt == "csv":
            return list(csv.DictReader(io.StringIO(content)))
        elif fmt == "xml":
            return self._xml_to_dict(ET.fromstring(content))
        else:
            return content

    def _format_output(self, data: Any, fmt: str) -> str:
        if fmt == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)
        elif fmt == "yaml":
            if not HAS_YAML:
                raise ImportError("PyYAML not installed")
            return yaml.dump(data, default_flow_style=False, allow_unicode=True)
        elif fmt == "toml":
            if not HAS_TOML:
                raise ImportError("tomli not installed")
            return toml.dumps(data)
        elif fmt == "csv":
            return self._to_csv(data)
        elif fmt == "xml":
            return self._to_xml(data)
        else:
            return str(data)

    def _to_csv(self, data: Any) -> str:
        if isinstance(data, dict):
            data = [data]
        if not data or not isinstance(data, list):
            return str(data)
        headers = list(data[0].keys()) if isinstance(data[0], dict) else []
        if not headers:
            return str(data)
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        for row in data:
            if isinstance(row, dict):
                writer.writerow(row)
        return output.getvalue()

    def _xml_to_dict(self, element) -> Dict:
        result = {}
        if element.attrib:
            result['@attributes'] = element.attrib
        if element.text and element.text.strip():
            if len(element) == 0:
                return element.text.strip()
            result['#text'] = element.text.strip()
        for child in element:
            child_data = self._xml_to_dict(child)
            if child.tag in result:
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data
        return result

    def _to_xml(self, data: Any, root_tag: str = "data") -> str:
        def build(parent, d):
            for k, v in d.items():
                if isinstance(v, dict):
                    child = ET.SubElement(parent, str(k))
                    build(child, v)
                elif isinstance(v, list):
                    for item in v:
                        child = ET.SubElement(parent, str(k))
                        if isinstance(item, dict):
                            build(child, item)
                        else:
                            child.text = str(item)
                else:
                    ET.SubElement(parent, str(k)).text = str(v)
        root = ET.Element(root_tag)
        if isinstance(data, dict):
            build(root, data)
        ET.indent(root)
        return ET.tostring(root, encoding='unicode', method='xml')

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "Data string to convert"},
                "file": {"type": "string", "description": "Input file path"},
                "from_format": {"type": "string", "description": "Input format"},
                "to_format": {"type": "string", "description": "Output format: json, yaml, toml, csv, xml, text"},
                "output": {"type": "string", "description": "Output file path (optional)"}
            },
            "required": ["to_format"]
        }


class CreateDataFileTool(Tool):
    """Create any data file from structured content."""

    def __init__(self):
        super().__init__(
            name="create_data_file",
            description="""Create a data file in any format.
Input: {"data": "{...}", "output": "file.json", "format": "json"}
Or: {"data": "[...]", "output": "file.yaml", "format": "yaml"}
Formats: json, yaml, toml, csv, xml, txt""",
        )

    async def execute(self, data: str = "", output: str = "", format: str = "", **kwargs) -> ToolResult:
        try:
            if not output:
                return ToolResult(success=False, result=None, error="No output file path provided")

            fmt = format or os.path.splitext(output)[1].lstrip('.')
            parsed = json.loads(data) if data.strip().startswith(('{', '[')) else data

            os.makedirs(os.path.dirname(output) or '.', exist_ok=True)

            if fmt == "json":
                with open(output, 'w', encoding='utf-8') as f:
                    json.dump(parsed, f, indent=2, ensure_ascii=False)
            elif fmt in ("yaml", "yml"):
                if not HAS_YAML:
                    return ToolResult(success=False, result=None, error="PyYAML not installed")
                with open(output, 'w', encoding='utf-8') as f:
                    yaml.dump(parsed, f, default_flow_style=False, allow_unicode=True)
            elif fmt == "toml":
                if not HAS_TOML:
                    return ToolResult(success=False, result=None, error="tomli not installed")
                with open(output, 'wb') as f:
                    toml.dump(parsed, f)
            elif fmt == "csv":
                self._write_csv(output, parsed)
            elif fmt == "xml":
                self._write_xml(output, parsed)
            elif fmt in ("txt", "text"):
                with open(output, 'w', encoding='utf-8') as f:
                    f.write(json.dumps(parsed, indent=2) if isinstance(parsed, (dict, list)) else str(parsed))
            else:
                return ToolResult(success=False, result=None,
                    error=f"Format '{fmt}' not supported. Use create_pdf, create_docx, create_xlsx, or create_pptx for that format.")

            return ToolResult(success=True, result=f"Created {output}")
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _write_csv(self, output: str, data):
        if isinstance(data, dict):
            data = [data]
        if not data or not isinstance(data, list):
            with open(output, 'w', encoding='utf-8') as f:
                f.write(str(data))
            return
        headers = list(data[0].keys()) if isinstance(data[0], dict) else []
        with open(output, 'w', encoding='utf-8', newline='') as f:
            if headers:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                for row in data:
                    if isinstance(row, dict):
                        writer.writerow(row)

    def _write_xml(self, output: str, data):
        def build(parent, d):
            for k, v in d.items():
                if isinstance(v, dict):
                    child = ET.SubElement(parent, str(k))
                    build(child, v)
                elif isinstance(v, list):
                    for item in v:
                        child = ET.SubElement(parent, str(k))
                        if isinstance(item, dict):
                            build(child, item)
                        else:
                            child.text = str(item)
                else:
                    ET.SubElement(parent, str(k)).text = str(v)
        root = ET.Element("data")
        if isinstance(data, dict):
            build(root, data)
        ET.indent(root)
        with open(output, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write(ET.tostring(root, encoding='unicode'))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "Content as JSON string"},
                "output": {"type": "string", "description": "Output file path"},
                "format": {"type": "string", "description": "Format: json, yaml, toml, csv, xml, txt"}
            },
            "required": ["output"]
        }