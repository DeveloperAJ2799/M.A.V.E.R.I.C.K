"""Init command - initialize new projects."""
import asyncio
import argparse
import shutil
from pathlib import Path
from typing import Optional, Any

from .base import Command


class InitCommand(Command):
    """Initialize a new project command."""

    name = "init"
    help = "Initialize a new project or create a skill/plugin template"
    aliases = ["i"]

    def __init__(self):
        self.parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog="maverickbot init")
        
        sub = parser.add_subparsers(dest="type", help="What to initialize")
        
        project = sub.add_parser("project", help="Initialize a new project")
        project.add_argument("--name", "-n", default="my-project", help="Project name")
        
        skill = sub.add_parser("skill", help="Create skill template")
        skill.add_argument("name", help="Skill name")
        skill.add_argument("--python", action="store_true", help="Use Python workflow")
        
        plugin = sub.add_parser("plugin", help="Create plugin template")
        plugin.add_argument("name", help="Plugin name")
        plugin.add_argument("type", choices=["tool", "provider"], help="Plugin type")
        
        tool = sub.add_parser("tool", help="Create a new tool quickly")
        tool.add_argument("name", help="Tool name")
        tool.add_argument("--description", "-d", default="Custom tool", help="Tool description")
        tool.add_argument("--parameter", "-p", action="append", help="Parameter (name:type:description)")
        
        return parser

    async def execute(self, args: argparse.Namespace, context: dict) -> Optional[Any]:
        """Execute the init command."""
        from colorama import Fore, Style
        
        if args.type == "project":
            self._init_project(args, Fore, Style)
        elif args.type == "skill":
            self._init_skill(args, Fore, Style)
        elif args.type == "plugin":
            self._init_plugin(args, Fore, Style)
        elif args.type == "tool":
            self._init_tool(args, Fore, Style)
        else:
            print(f"{Fore.RED}Usage: maverickbot init project|skill|plugin|tool{Style.RESET_ALL}")

    def _init_project(self, args, Fore, Style):
        """Initialize a new project."""
        project_dir = Path.cwd() / args.name
        
        if project_dir.exists():
            print(f"{Fore.RED}Directory already exists: {args.name}{Style.RESET_ALL}")
            return
        
        project_dir.mkdir()
        
        (project_dir / "maverickbot.yaml").write_text("""# MaverickBot Configuration
provider: lmstudio
model: google/gemma-4-e2b
lmurl: http://127.0.0.1:1234
temperature: 0.7
max_tokens: 4096
multi_agent: false
""")
        
        (project_dir / "README.md").write_text(f"""# {args.name}

A MaverickBot project.

## Setup
```bash
cd {args.name}
pip install maverickbot
```

## Run
```bash
maverickbot chat
```
""")
        
        print(f"{Fore.GREEN}Initialized project: {args.name}{Style.RESET_ALL}")
        print(f"  {Fore.YELLOW}cd {args.name}{Style.RESET_ALL}")
        print(f"  {Fore.YELLOW}maverickbot chat{Style.RESET_ALL}")

    def _init_skill(self, args, Fore, Style):
        """Initialize a skill template."""
        skills_dir = Path("skills/custom")
        
        if not skills_dir.exists():
            print(f"{Fore.RED}skills/custom directory not found{Style.RESET_ALL}")
            return
        
        skill_dir = skills_dir / args.name
        skill_dir.mkdir(exist_ok=True)
        
        if args.python:
            (skill_dir / "skill.yaml").write_text(f"""skill:
  name: "{args.name}"
  version: "1.0.0"
  description: "Custom skill with Python workflow"
  tools_required:
    - "read_file"
    - "write_file"
  system_prompt: |
    You are a custom skill that does specialized work.
  workflow: "custom"
  config:
    max_iterations: 10
""")
            (skill_dir / "workflow.py").write_text(f'''"""Custom workflow for {args.name}."""
from typing import Dict, Any


class CustomWorkflow:
    """Custom workflow handler."""
    
    def __init__(self, config: Dict[str, Any], tool_registry):
        self.config = config
        self.tool_registry = tool_registry
    
    async def execute(self, input_data: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the workflow."""
        return {{"status": "completed", "result": "Done"}}
''')
        else:
            (skill_dir / "skill.yaml").write_text(f"""skill:
  name: "{args.name}"
  version: "1.0.0"
  description: "Simple skill with YAML workflow"
  tools_required:
    - "read_file"
  system_prompt: |
    You are a helpful assistant specialized in this task.
  workflow:
    - action: "process"
      prompt: "Process the input"
  config:
    setting: "value"
""")
        
        print(f"{Fore.GREEN}Created skill: {args.name}{Style.RESET_ALL}")
        print(f"  Location: {skill_dir}")
        print(f"  Edit: {skill_dir}/skill.yaml")

    def _init_plugin(self, args, Fore, Style):
        """Initialize a plugin template."""
        if args.type == "tool":
            plugin_dir = Path(f"plugins/tools/{args.name}")
        else:
            plugin_dir = Path(f"plugins/providers/{args.name}")
        
        plugin_dir.mkdir(parents=True, exist_ok=True)
        
        if args.type == "tool":
            (plugin_dir / "manifest.yaml").write_text(f"""name: "{args.name}"
version: "1.0.0"
author: ""
description: "Custom tool"
entry_point: "MyTool"
dependencies: []
tags: ["custom"]
""")
            (plugin_dir / "__init__.py").write_text(f'''"""Custom tool: {args.name}."""
from maverickbot.agent.tools.base import Tool, ToolResult


class MyTool(Tool):
    """Custom tool implementation."""
    
    def __init__(self):
        super().__init__(
            name="{args.name}",
            description="What this tool does"
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        try:
            result = "Tool executed"
            return ToolResult(success=True, result=result)
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))
    
    def _get_parameters_schema(self):
        return {{
            "type": "object",
            "properties": {{
                "input": {{"type": "string", "description": "Input"}}
            }},
            "required": ["input"]
        }}
''')
        else:
            (plugin_dir / "manifest.yaml").write_text(f"""name: "{args.name}"
version: "1.0.0"
author: ""
description: "Custom LLM provider"
entry_point: "MyProvider"
dependencies: []
tags: ["llm"]
""")
            (plugin_dir / "__init__.py").write_text(f'''"""Custom provider: {args.name}."""
from maverickbot.providers.base import LLMProvider, LLMResponse


class MyProvider(LLMProvider):
    """Custom provider implementation."""
    
    def __init__(self, model: str = "default", **kwargs):
        super().__init__(model)
        self.endpoint = "https://api.example.com/v1/chat"
    
    async def chat(self, messages, temperature=0.7, max_tokens=4096, tools=None):
        return LLMResponse(content="Response", finish_reason="stop")
    
    async def list_models(self):
        return [self.model]
''')
        
        print(f"{Fore.GREEN}Created {args.type} plugin: {args.name}{Style.RESET_ALL}")
        print(f"  Location: {plugin_dir}")
        print(f"  Edit: {plugin_dir}/manifest.yaml")
        print(f"  Run: maverickbot --reload")

    def _init_tool(self, args, Fore, Style):
        """Initialize a quick tool in agent tools."""
        tools_dir = Path(__file__).parent.parent.parent / "agent" / "tools"
        
        if not tools_dir.exists():
            print(f"{Fore.RED}Tools directory not found: {tools_dir}{Style.RESET_ALL}")
            return
        
        tool_name = args.name.lower().replace("_", "_")
        tool_file = tools_dir / f"{tool_name}.py"
        
        if tool_file.exists():
            print(f"{Fore.RED}Tool already exists: {tool_name}.py{Style.RESET_ALL}")
            return
        
        params = {}
        if args.parameter:
            for p in args.parameter:
                parts = p.split(":")
                if len(parts) >= 3:
                    param_name, param_type, param_desc = parts[0], parts[1], parts[2]
                    params[param_name] = {"type": param_type, "description": param_desc}
        
        class_name = "".join(word.capitalize() for word in tool_name.split("_")) + "Tool"
        
        tool_code = f'''"""Tool: {tool_name}."""
from typing import Any, Dict
from .base import Tool, ToolResult


class {class_name}(Tool):
    """Tool for {args.description.lower()}."""

    def __init__(self):
        super().__init__(
            name="{tool_name}",
            description="{args.description}",
        )

    async def execute(self, **kwargs) -> ToolResult:
        try:
            # TODO: Implement your tool logic here
            # Access parameters via kwargs, e.g., kwargs.get("input")
            
            result = "Tool executed successfully"
            return ToolResult(success=True, result=result)
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {{
            "type": "object",
            "properties": {{
                "input": {{"type": "string", "description": "Input"}}
            }},
            "required": ["input"]
        }}
'''
        
        tool_file.write_text(tool_code)
        
        print(f"{Fore.GREEN}Created tool: {tool_name}{Style.RESET_ALL}")
        print(f"  Location: {tool_file}")
        print(f"  Edit: {tool_file}")
        print(f"  Restart chat to use the new tool")