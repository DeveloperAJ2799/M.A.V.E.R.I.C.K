"""JSON and YAML data tools."""
import json
import yaml
from typing import Any, Dict
from .base import Tool, ToolResult


class ParseJsonTool(Tool):
    """Tool for parsing and validating JSON."""

    def __init__(self):
        super().__init__(
            name="parse_json",
            description="Parse and validate JSON string. Input: JSON with 'data' (string or file path).",
        )

    async def execute(self, **kwargs) -> ToolResult:
        data = kwargs.get("data", "")
        file_path = kwargs.get("file", "")
        
        try:
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as f:
                    parsed = json.load(f)
            else:
                parsed = json.loads(data)
            
            # Pretty print
            formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
            if len(formatted) > 5000:
                formatted = formatted[:5000] + "\n... (truncated)"
            
            return ToolResult(success=True, result=f"Valid JSON:\n{formatted}")
        except json.JSONDecodeError as e:
            return ToolResult(success=False, result=None, error=f"Invalid JSON: {e}")
        except FileNotFoundError:
            return ToolResult(success=False, result=None, error=f"File not found: {file_path}")
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "JSON string to parse"},
                "file": {"type": "string", "description": "Path to JSON file"}
            }
        }


class ToYamlTool(Tool):
    """Tool for converting JSON to YAML."""

    def __init__(self):
        super().__init__(
            name="to_yaml",
            description="Convert JSON to YAML. Input: JSON with 'data' (string/file), optional 'output' file path.",
        )

    async def execute(self, **kwargs) -> ToolResult:
        data = kwargs.get("data", "")
        file_path = kwargs.get("file", "")
        output = kwargs.get("output", "")
        
        try:
            # Parse JSON
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as f:
                    parsed = json.load(f)
            else:
                parsed = json.loads(data)
            
            # Convert to YAML
            yaml_str = yaml.dump(parsed, default_flow_style=False, allow_unicode=True)
            
            if output:
                with open(output, 'w', encoding='utf-8') as f:
                    f.write(yaml_str)
                return ToolResult(success=True, result=f"Saved to {output}")
            
            return ToolResult(success=True, result=yaml_str)
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "JSON string to convert"},
                "file": {"type": "string", "description": "Path to JSON file"},
                "output": {"type": "string", "description": "Output YAML file path"}
            }
        }


class FromYamlTool(Tool):
    """Tool for converting YAML to JSON."""

    def __init__(self):
        super().__init__(
            name="from_yaml",
            description="Convert YAML to JSON. Input: JSON with 'data' (string/file), optional 'output' file path.",
        )

    async def execute(self, **kwargs) -> ToolResult:
        data = kwargs.get("data", "")
        file_path = kwargs.get("file", "")
        output = kwargs.get("output", "")
        
        try:
            # Parse YAML
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as f:
                    parsed = yaml.safe_load(f)
            else:
                parsed = yaml.safe_load(data)
            
            # Convert to JSON
            json_str = json.dumps(parsed, indent=2, ensure_ascii=False)
            
            if output:
                with open(output, 'w', encoding='utf-8') as f:
                    f.write(json_str)
                return ToolResult(success=True, result=f"Saved to {output}")
            
            return ToolResult(success=True, result=json_str)
        except yaml.YAMLError as e:
            return ToolResult(success=False, result=None, error=f"Invalid YAML: {e}")
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "YAML string to convert"},
                "file": {"type": "string", "description": "Path to YAML file"},
                "output": {"type": "string", "description": "Output JSON file path"}
            }
        }


class ValidateJsonTool(Tool):
    """Tool for JSON schema validation."""

    def __init__(self):
        super().__init__(
            name="validate_json",
            description="Validate JSON against a schema. Input: JSON with 'data' and 'schema' (both required).",
        )

    async def execute(self, **kwargs) -> ToolResult:
        data = kwargs.get("data", "")
        schema = kwargs.get("schema", "")
        
        try:
            # Try to import jsonschema
            import jsonschema
            
            json_data = json.loads(data) if isinstance(data, str) else data
            json_schema = json.loads(schema) if isinstance(schema, str) else schema
            
            jsonschema.validate(json_data, json_schema)
            
            return ToolResult(success=True, result="JSON is valid against schema")
            
        except ImportError:
            return ToolResult(success=False, result=None, error="jsonschema not installed. Install with: pip install jsonschema")
        except jsonschema.ValidationError as e:
            return ToolResult(success=False, result=None, error=f"Validation failed: {e.message}")
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "data": {"type": "string", "description": "JSON data to validate"},
                "schema": {"type": "string", "description": "JSON schema to validate against"}
            },
            "required": ["data", "schema"]
        }