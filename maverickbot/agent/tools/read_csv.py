"""Read CSV tool."""
from typing import Any, Dict
from .base import Tool, ToolResult


class ReadCsvTool(Tool):
    """Tool for reading CSV files."""

    def __init__(self):
        super().__init__(
            name="read_csv",
            description="Read a CSV file and return data. Input: JSON with 'file' (path), 'delimiter' (optional).",
        )

    async def execute(self, **kwargs) -> ToolResult:
        try:
            import csv
            
            file_path = kwargs.get("file", "")
            delimiter = kwargs.get("delimiter", ",")
            
            if not file_path:
                return ToolResult(success=False, result=None, error="No file specified")
            
            with open(file_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f, delimiter=delimiter)
                rows = list(reader)
            
            headers = rows[0] if rows else []
            data = rows[1:] if len(rows) > 1 else []
            
            result = f"Columns: {headers}\nRows: {len(data)}\n\n"
            result += "Headers: " + str(headers) + "\n\n"
            result += "First 10 rows:\n"
            for i, row in enumerate(data[:10]):
                result += f"{i+1}. {row}\n"
            
            return ToolResult(success=True, result=result)
        except FileNotFoundError:
            return ToolResult(success=False, result=None, error=f"File not found: {file_path}")
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file": {"type": "string", "description": "Path to the CSV file"},
                "delimiter": {"type": "string", "description": "CSV delimiter (default: ,)"}
            },
            "required": ["file"]
        }