"""Chat command - interactive chat with the agent."""
import asyncio
import argparse
import os
import sys
from typing import Optional, Any, Dict, List
from pathlib import Path

# Fix encoding for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from maverickbot.providers import ProviderRegistry
from maverickbot.agent import AgentRunner, ToolRegistry
from maverickbot.agent.tools import (
    ReadFileTool, WriteFileTool, AppendFileTool, 
    DeleteFileTool, ListDirectoryTool, CopyFileTool, MoveFileTool,
    CreateDirectoryTool, FileExistsTool, GetFileInfoTool,
    ShellTool, SearchTool,
    CreatePPTXTool, CreatePdfTool, ReadPdfTool, CreateDocxTool, ReadDocxTool,
    CreateXlsxTool, ReadXlsxTool, CreateImageTool, ReadImageTool,
    TextToSpeechTool, ReadCsvTool, FetchUrlTool, ExecuteCodeTool,
    GitStatusTool, GitLogTool, GitDiffTool, GitBranchTool,
    ParseJsonTool, ToYamlTool, FromYamlTool, ValidateJsonTool,
    SystemInfoTool, ClipboardReadTool, ClipboardWriteTool, NotifyTool,
    ToolResult
)
from maverickbot.multiagent import MultiAgentOrchestrator
from maverickbot.core import Registry
from maverickbot.mcp import MCPClient
from maverickbot.cli.config import CLIConfig
from loguru import logger
from .base import Command


class ChatCommand(Command):
    """Interactive chat command."""

    name = "chat"
    help = "Start an interactive chat session"
    aliases = ["c", "shell", "repl"]

    def __init__(self):
        self.parser = self._create_parser()
        self.runner = None
        self.registry = None
        self.orchestrator = None
        self.active_skills = []

    def _create_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="maverickbot chat",
            description="Start an interactive chat session",
        )
        parser.add_argument(
            "--prompt", "-c",
            help="Single prompt to execute (non-interactive)",
        )
        parser.add_argument(
            "--multi-agent", "-ma",
            action="store_true",
            help="Enable multi-agent system",
        )
        return parser

    async def execute(self, args: argparse.Namespace, context: dict) -> Optional[Any]:
        """Execute the chat command."""
        config = context.get("config")
        
        # Enable debug if set
        if config.debug:
            import os
            os.environ["LOGURU_LEVEL"] = "DEBUG"
        
        # Initialize session manager
        from maverickbot.cli.commands.session import SessionManager
        session_mgr = SessionManager()
        context["session_manager"] = session_mgr
        
        import os
        api_key = None
        base_url = None
        
        if config.provider == "nvidia":
            api_key = config.nvidia_api_key
            base_url = "https://integrate.api.nvidia.com/v1"
        elif config.provider == "groq":
            api_key = os.environ.get("GROQ_API_KEY")
        elif config.provider == "lmstudio":
            base_url = config.lmurl if config.lmurl else "http://127.0.0.1:1234"
        
        if not api_key:
            api_key = os.environ.get("NVIDIA_API_KEY")
        
        provider = ProviderRegistry.create(
            config.provider,
            model=config.model,
            base_url=base_url,
            api_key=api_key,
        )

        tool_registry = ToolRegistry()
        tool_registry.register(ReadFileTool())
        tool_registry.register(WriteFileTool())
        tool_registry.register(AppendFileTool())
        tool_registry.register(ShellTool())
        tool_registry.register(SearchTool())
        tool_registry.register(CreatePPTXTool())
        tool_registry.register(CreatePdfTool())
        tool_registry.register(ReadPdfTool())
        tool_registry.register(CreateDocxTool())
        tool_registry.register(ReadDocxTool())
        tool_registry.register(CreateXlsxTool())
        tool_registry.register(ReadXlsxTool())
        tool_registry.register(CreateImageTool())
        tool_registry.register(ReadImageTool())
        tool_registry.register(TextToSpeechTool())
        tool_registry.register(ReadCsvTool())
        tool_registry.register(FetchUrlTool())
        tool_registry.register(ExecuteCodeTool())
        
        # File management tools
        tool_registry.register(DeleteFileTool())
        tool_registry.register(ListDirectoryTool())
        tool_registry.register(CopyFileTool())
        tool_registry.register(MoveFileTool())
        tool_registry.register(CreateDirectoryTool())
        tool_registry.register(FileExistsTool())
        tool_registry.register(GetFileInfoTool())
        
        # Git tools
        tool_registry.register(GitStatusTool())
        tool_registry.register(GitLogTool())
        tool_registry.register(GitDiffTool())
        tool_registry.register(GitBranchTool())
        
        # Data tools
        tool_registry.register(ParseJsonTool())
        tool_registry.register(ToYamlTool())
        tool_registry.register(FromYamlTool())
        tool_registry.register(ValidateJsonTool())
        
        # System tools
        tool_registry.register(SystemInfoTool())
        tool_registry.register(ClipboardReadTool())
        tool_registry.register(ClipboardWriteTool())
        tool_registry.register(NotifyTool())

        # Initialize MCP client (use /mcp connect to enable)
        mcp_client = MCPClient()
        self.mcp_client = mcp_client

        # Connect to MCP servers from config
        await self._connect_mcp_servers(mcp_client, tool_registry, config)

        # Auto-discover tools from agent/tools directory
        self._auto_discover_tools(tool_registry)

        self.registry = Registry()
        self.registry.initialize()

        for tool_data in self.registry.get_all_tools().values():
            try:
                tool_class = tool_data.get("class")
                if tool_class:
                    tool_registry.register(tool_class())
            except Exception as e:
                logger.warning(f"Failed to register plugin tool: {e}")

        if args.multi_agent:
            self.orchestrator = MultiAgentOrchestrator(
                provider=provider,
                tool_registry=tool_registry,
            )
            await self.orchestrator.initialize()

        tool_suggestion_prompt = """

## Available Tools - USE THESE FOR FILE OPERATIONS

### Document Creation:
- **create_pptx**: Create PowerPoint. Input: {"slides": [{"title": "X", "content": ["a", "b"]}], "output": "file.pptx"}
- **create_pdf**: Create PDF. Input: {"content": "text", "output": "file.pdf"}
- **create_docx**: Create Word doc. Input: {"content": "text", "title": "Title", "output": "file.docx"}
- **create_xlsx**: Create Excel. Input: {"data": [["row1"], ["row2"]], "headers": ["col1"], "output": "file.xlsx"}

### Document Reading:
- **read_pdf**: Read PDF. Input: {"file": "path/to/file.pdf"}
- **read_docx**: Read Word. Input: {"file": "path/to/file.docx"}
- **read_xlsx**: Read Excel. Input: {"file": "path/to/file.xlsx"}
- **read_csv**: Read CSV. Input: {"file": "path/to/file.csv"}

### Image & Audio:
- **create_image**: Create image from text. Input: {"text": "Hello", "output": "image.png"}
- **read_image**: Get image info. Input: {"file": "path/to/image.png"}
- **text_to_speech**: Text to audio. Input: {"text": "Hello", "output": "speech.mp3", "lang": "en"}

### Basic File Operations:
- **read_file**: Read any text file
- **write_file**: Write text to file
- **append_file**: Append to file

### Web & Search:
- **search**: Search the web. Input: {"query": "search terms"}
- **fetch_url**: Get full content from a URL. Input: {"url": "https://..."}

### Code Execution:
- **execute_code**: Run Python code. Input: {"code": "print('hello')", "timeout": 30}
  - Use for calculations, data processing, code testing
  - Maximum 60 second timeout

### Git Operations:
- **git_status**: Check git repo status
- **git_log**: View recent commits. Input: {"limit": 10}
- **git_diff**: See changes. Input: {"file": "path/to/file"}
- **git_branch**: List/create/delete branches

### Data & JSON:
- **parse_json**: Parse and validate JSON
- **to_yaml**: Convert JSON to YAML
- **from_yaml**: Convert YAML to JSON
- **validate_json**: Validate JSON against schema

### System:
- **system_info**: Get system information (CPU, RAM, disk)
- **clipboard_read**: Read clipboard content
- **clipboard_write**: Write to clipboard. Input: {"text": "content"}
- **notify**: Send system notification. Input: {"message": "text", "title": "M.A.V.E.R.I.C.K"}
- **shell**: Execute shell commands

## File Operations Protocol:
1. When user asks to CREATE a file (PDF, DOCX, XLSX, PPTX, image, audio) → use appropriate CREATE tool
2. When user asks to READ/EXTRACT from file → use appropriate READ tool
3. When user asks for something not covered above → use shell tool
4. When NO tool exists for needed operation → use [NEEDS_TOOL: description] format

## Safety Guidelines:
- For DELETE operations (rm, del, remove), ask for confirmation first
- For NETWORK requests (curl, wget), warn user about external connections
- For SYSTEM commands that modify files, confirm before executing
- If unsure about a command's safety, ask user before proceeding

## Dangerous Actions That Need Confirmation:
- Deleting files or folders
- Formatting drives or wiping data
- Installing packages or making system changes
- Sending data to external URLs (not search/fetch tools)
- Modifying git history or force pushing
"""

        enhanced_prompt = config.system_prompt + tool_suggestion_prompt

        self.runner = AgentRunner(
            provider=provider,
            tool_registry=tool_registry,
            system_prompt=enhanced_prompt,
        )

        if args.prompt:
            response = await self._single_prompt(args.prompt, args.multi_agent)
            print("=== Response ===")
            print(response)
            print("=== End ===")
            try:
                await self._cleanup()
            except Exception:
                pass
            return
        
        return await self._interactive_mode(args.multi_agent)

    async def _single_prompt(self, prompt: str, multi_agent: bool) -> str:
        """Execute a single prompt."""
        # Check for skill commands
        if prompt.lower().startswith("/skill"):
            parts = prompt.split()
            if len(parts) >= 2:
                skill_name = parts[1]
                if self.registry.activate_skill(skill_name):
                    print(f"Skill activated: {skill_name}")
                    active = self.registry.get_active_skills()
                    print(f"  Active skills: {', '.join(active)}")
                    self._update_system_prompt_with_skills()
                    return f"Skill '{skill_name}' activated. Your system prompt has been updated."
                else:
                    return f"Skill not found: {skill_name}"
            else:
                active = self.registry.get_active_skills()
                return f"Active skills: {', '.join(active) if active else 'None'}\nUse /skill <name> to activate"
        
        if prompt.lower() == "skills":
            self._list_available_skills()
            return ""
        
        # Create skill: "create skill <name> <description>"
        if prompt.lower().startswith("create skill "):
            return await self._create_skill_from_chat(prompt)
        
        # MCP commands
        if prompt.lower().startswith("/mcp"):
            return self._handle_mcp_command(prompt) or ""
        
        if multi_agent and self.orchestrator:
            result = await self.orchestrator.process(prompt)
            if result.get("result", {}).get("final_result"):
                response = result["result"]["final_result"]
            else:
                response = str(result.get("result", {}))
        else:
            try:
                response = await self.runner.chat(prompt)
            except Exception as e:
                import traceback
                traceback.print_exc()
                return f"Error: {str(e)}"
        
        self._check_tool_suggestions(response)
        return response

    def _check_tool_suggestions(self, response: str):
        """Check if agent requested a new tool."""
        import re
        from colorama import Fore, Style
        
        pattern = r'\[NEEDS_TOOL:\s*([^\]]+)\]'
        matches = re.findall(pattern, response, re.IGNORECASE)
        
        if matches:
            print(f"\n{Fore.CYAN}💡 Tool Suggestion:{Style.RESET_ALL}")
            for match in matches:
                tool_desc = match.strip()
                print(f"  Agent needs: {Fore.YELLOW}{tool_desc}{Style.RESET_ALL}")
                print(f"  {Fore.GREEN}→ Create it: maverickbot init tool <name> --description \"{tool_desc}\"{Style.RESET_ALL}")
                print()

    async def _interactive_mode(self, multi_agent: bool):
        """Run interactive chat loop."""
        from colorama import Fore, Style
        from maverickbot.cli.banner import print_banner
        
        print_banner()
        print()
        
        if multi_agent:
            print(f"{Fore.GREEN}Multi-agent mode enabled!{Style.RESET_ALL}")
            agents = self.orchestrator.list_agents()
            print(f"Agents: {', '.join([a['name'] for a in agents])}")
        print(f"Type {Fore.YELLOW}help{Style.RESET_ALL} for commands, {Fore.YELLOW}exit{Style.RESET_ALL} to quit.\n")
        
        while True:
            try:
                user_input = input(f"{Fore.BLUE}> {Style.RESET_ALL}").strip()
                if not user_input:
                    continue
                
                if user_input.lower() in ["exit", "quit", "q"]:
                    print(f"{Fore.YELLOW}Goodbye!{Style.RESET_ALL}")
                    break

                if user_input.lower() == "help":
                    self._print_help()
                    continue
                
                if user_input.lower() == "clear":
                    import os
                    os.system("cls" if os.name == "nt" else "clear")
                    continue

                if user_input.lower() == "reset":
                    self.runner.reset()
                    print(f"{Fore.YELLOW}Session reset.{Style.RESET_ALL}")
                    continue
                
                if user_input.lower().startswith("/skill"):
                    parts = user_input.split()
                    if len(parts) >= 2:
                        skill_name = parts[1]
                        if self.registry.activate_skill(skill_name):
                            print(f"{Fore.GREEN}Skill activated: {skill_name}{Style.RESET_ALL}")
                            active = self.registry.get_active_skills()
                            print(f"  Active skills: {', '.join(active)}")
                            self._update_system_prompt_with_skills()
                        else:
                            print(f"{Fore.RED}Skill not found: {skill_name}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.YELLOW}Usage: /skill <name>{Style.RESET_ALL}")
                        print(f"  Active: {self.registry.get_active_skills()}")
                    continue
                
                if user_input.lower() == "skills":
                    self._list_available_skills()
                    continue
                
                if user_input.lower().startswith("/mcp"):
                    result = self._handle_mcp_command(user_input)
                    if result:
                        print(result)
                    continue

                response = await self._single_prompt(user_input, multi_agent)
                print(f"\n{Fore.GREEN}{response}{Style.RESET_ALL}\n")

            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Interrupted. Type 'exit' to quit.{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")

    def _print_help(self):
        """Print help message."""
        from colorama import Fore, Style
        print(f"""
{Fore.CYAN}Commands:{Style.RESET_ALL}
  {Fore.YELLOW}help{Style.RESET_ALL}     - Show this help
  {Fore.YELLOW}clear{Style.RESET_ALL}    - Clear screen
  {Fore.YELLOW}reset{Style.RESET_ALL}    - Reset conversation
  {Fore.YELLOW}exit{Style.RESET_ALL}    - Exit

{Fore.CYAN}File Creation Tools:{Style.RESET_ALL}
  create_pptx, create_pdf, create_docx, create_xlsx, create_image, text_to_speech

{Fore.CYAN}File Reading Tools:{Style.RESET_ALL}
  read_file, read_pdf, read_docx, read_xlsx, read_csv, read_image

{Fore.CYAN}System Tools:{Style.RESET_ALL}
  write_file, append_file, shell, search

{Fore.CYAN}Skills:{Style.RESET_ALL}
  /skill <name> to activate
  create skill <name> <description>

{Fore.CYAN}MCP Servers:{Style.RESET_ALL}
  /mcp list - List connected MCP servers
  /mcp status - Show MCP connection status

{Fore.CYAN}Multi-Agent:{Style.RESET_ALL}
  researcher, coder, writer (use --multi-agent flag)
""")

    def _auto_discover_tools(self, tool_registry):
        """Auto-discover tools from agent/tools directory."""
        import importlib
        import inspect
        from pathlib import Path
        from maverickbot.agent.tools import Tool
        
        tools_dir = Path(__file__).parent.parent.parent / "agent" / "tools"
        
        for py_file in tools_dir.glob("*.py"):
            if py_file.name.startswith("_") or py_file.name == "base.py":
                continue
            
            module_name = f"maverickbot.agent.tools.{py_file.stem}"
            try:
                module = importlib.import_module(module_name)
                
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) 
                        and issubclass(obj, Tool) 
                        and obj is not Tool
                        and obj not in [ReadFileTool, WriteFileTool, AppendFileTool, ShellTool, SearchTool, CreatePPTXTool]):
                        
                        existing = tool_registry.get(obj().name)
                        if not existing:
                            tool_registry.register(obj())
                            logger.info(f"Auto-discovered tool: {obj().name}")
            except Exception as e:
                logger.debug(f"Could not load {module_name}: {e}")
    
    def _update_system_prompt_with_skills(self):
        """Update system prompt with active skills."""
        active_skills = self.registry.get_active_skills()
        if active_skills and self.runner:
            skill_configs = self.registry.get_active_skill_configs()
            skill_prompts = []
            for cfg in skill_configs:
                if cfg.get("system_prompt"):
                    skill_prompts.append(f"\n## Skill: {cfg.get('name')}\n{cfg.get('system_prompt')}")
            
            if skill_prompts:
                base_prompt = self.runner.system_prompt
                enhanced = base_prompt + "\n" + "\n".join(skill_prompts)
                self.runner.system_prompt = enhanced
    
    def _list_available_skills(self):
        """List all available skills."""
        from colorama import Fore, Style
        from pathlib import Path
        import yaml
        
        print(f"\n{Fore.CYAN}Available Skills:{Style.RESET_ALL}")
        
        available_path = Path(__file__).parent.parent.parent / "skills" / "available"
        custom_path = Path(__file__).parent.parent.parent / "skills" / "custom"
        
        skills_found = False
        
        for path in [available_path, custom_path]:
            if path.exists():
                for skill_dir in path.iterdir():
                    if skill_dir.is_dir() and (skill_dir / "skill.yaml").exists():
                        import yaml
                        with open(skill_dir / "skill.yaml") as f:
                            data = yaml.safe_load(f)
                            skill = data.get("skill", {})
                            print(f"  {Fore.YELLOW}{skill_dir.name}{Style.RESET_ALL}: {skill.get('description', 'No description')}")
                            skills_found = True
        
        if not skills_found:
            print(f"  {Fore.YELLOW}No skills found{Style.RESET_ALL}")
        
        active = self.registry.get_active_skills()
        if active:
            print(f"\n{Fore.GREEN}Active: {', '.join(active)}{Style.RESET_ALL}")
        
        print(f"\n{Fore.CYAN}Usage:{Style.RESET_ALL} /skill <name> to activate")
    
    async def _create_skill_from_chat(self, prompt: str) -> str:
        """Create a skill from chat prompt."""
        from pathlib import Path
        import re
        import yaml
        
        # Parse: "create skill <name> <description>"
        pattern = r'create skill\s+(\w+)\s+(.+)'
        match = re.match(pattern, prompt, re.IGNORECASE)
        
        if not match:
            return "Usage: create skill <name> <description>\nExample: create skill coder Write efficient Python code"
        
        skill_name = match.group(1).lower().replace(" ", "_")
        description = match.group(2).strip()
        
        # Create skill directory
        base_path = Path(__file__).parent.parent.parent
        custom_skills_path = base_path / "skills" / "custom" / skill_name
        custom_skills_path.mkdir(parents=True, exist_ok=True)
        
        # Create skill.yaml
        skill_yaml = {
            "skill": {
                "name": skill_name,
                "version": "1.0.0",
                "description": description,
                "tools_required": [],
                "system_prompt": f"You are a specialized assistant focused on: {description}",
                "workflow": [
                    {
                        "action": "assist",
                        "prompt": f"Help user with {description}"
                    }
                ],
                "config": {}
            }
        }
        
        with open(custom_skills_path / "skill.yaml", "w") as f:
            yaml.dump(skill_yaml, f, default_flow_style=False)
        
        # Reload skills
        self.registry.initialize()
        
        return f"Skill '{skill_name}' created successfully!\nDescription: {description}\nUse /skill {skill_name} to activate"

    async def _connect_mcp_servers(self, mcp_client: MCPClient, tool_registry: ToolRegistry, config: CLIConfig):
        """Connect to MCP servers from config and register their tools."""
        from colorama import Fore, Style

        if not mcp_client._mcp_available:
            print(f"{Fore.YELLOW}⚠ MCP SDK not installed. Run: pip install mcp[cli]{Style.RESET_ALL}")
            return

        home_dir = str(Path.home())
        servers_to_connect = []

        if config.mcp_servers is not None:
            for name, server_config in config.mcp_servers.items():
                if not server_config.get("enabled", True):
                    continue
                servers_to_connect.append({
                    "name": name,
                    "type": server_config.get("type", "stdio"),
                    "command": server_config.get("command"),
                    "args": server_config.get("args", []),
                    "env": server_config.get("env", {}),
                    "url": server_config.get("url"),
                })
        elif config.mcp_servers is None:
            servers_to_connect = self._get_default_servers(home_dir)

        if not servers_to_connect:
            print(f"{Fore.YELLOW}⚠ No MCP servers configured{Style.RESET_ALL}")
            return

        connected_count = 0
        failed_servers = []

        for server_config in servers_to_connect:
            server_name = server_config["name"]
            try:
                logger.info(f"Connecting to MCP server: {server_name}")
                connection = None

                if server_config.get("type") == "http" or server_config.get("url"):
                    connection = await asyncio.wait_for(
                        mcp_client.connect_http(
                            name=server_name,
                            url=server_config["url"],
                            headers=server_config.get("headers"),
                        ),
                        timeout=15
                    )
                else:
                    connection = await asyncio.wait_for(
                        mcp_client.connect_stdio(
                            name=server_name,
                            command=server_config["command"],
                            args=server_config["args"],
                            env=server_config.get("env", {})
                        ),
                        timeout=10
                    )

                if connection and connection.connected:
                    connected_count += 1
                    for tool in connection.tools:
                        mcp_tool = MCPToolWrapper(
                            server_name=connection.name,
                            tool_name=tool.name,
                            description=tool.description,
                            input_schema=tool.input_schema,
                            mcp_client=mcp_client
                        )
                        tool_registry.register(mcp_tool)
                    print(f"{Fore.GREEN}✓{Style.RESET_ALL} {server_name} ({len(connection.tools)} tools)")
                else:
                    error_msg = connection.last_error if connection else "Unknown error"
                    failed_servers.append((server_name, error_msg))
                    print(f"{Fore.RED}✗{Style.RESET_ALL} {server_name}: {error_msg}")

            except asyncio.TimeoutError:
                failed_servers.append((server_name, "Connection timeout"))
                print(f"{Fore.RED}✗{Style.RESET_ALL} {server_name}: Connection timeout")
            except Exception as e:
                logger.warning(f"MCP {server_name} connection failed: {e}")
                failed_servers.append((server_name, str(e)))
                print(f"{Fore.RED}✗{Style.RESET_ALL} {server_name}: {e}")

        if connected_count > 0:
            print(f"\n{Fore.CYAN}MCP: {connected_count} server(s) connected{Style.RESET_ALL}")
        elif not failed_servers:
            print(f"{Fore.YELLOW}⚠ MCP servers not available (optional){Style.RESET_ALL}")

    def _get_default_servers(self, home_dir: str) -> List[Dict[str, Any]]:
        """Get default MCP servers configuration."""
        return [
            {
                "name": "filesystem",
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", home_dir],
                "env": {}
            },
            {
                "name": "git",
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-git", home_dir],
                "env": {}
            },
            {
                "name": "memory",
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-memory"],
                "env": {}
            },
        ]

    async def _connect_mcp_servers_bg(self, mcp_client, tool_registry, config: CLIConfig):
        """Background MCP connection for auto-start."""
        from colorama import Fore, Style

        if not mcp_client._mcp_available:
            return

        home_dir = str(Path.home())
        servers_to_connect = []

        if config.mcp_servers is not None:
            for name, server_config in config.mcp_servers.items():
                if not server_config.get("enabled", True):
                    continue
                servers_to_connect.append({
                    "name": name,
                    "type": server_config.get("type", "stdio"),
                    "command": server_config.get("command"),
                    "args": server_config.get("args", []),
                    "env": server_config.get("env", {}),
                    "url": server_config.get("url"),
                })
        elif config.mcp_servers is None:
            servers_to_connect = self._get_default_servers(home_dir)

        connected_count = 0
        for server_config in servers_to_connect:
            try:
                connection = await asyncio.wait_for(
                    mcp_client.connect_stdio(
                        name=server_config["name"],
                        command=server_config["command"],
                        args=server_config["args"],
                        env=server_config.get("env", {})
                    ),
                    timeout=8
                )
                if connection and connection.connected:
                    connected_count += 1
                    for tool in connection.tools:
                        mcp_tool = MCPToolWrapper(
                            server_name=connection.name,
                            tool_name=tool.name,
                            description=tool.description,
                            input_schema=tool.input_schema,
                            mcp_client=mcp_client
                        )
                        tool_registry.register(mcp_tool)
                    print(f"{Fore.GREEN}✓{Style.RESET_ALL} MCP: {server_config['name']} ({len(connection.tools)} tools)")
            except Exception:
                pass

        if connected_count > 0:
            print(f"{Fore.CYAN}MCP: {connected_count} server(s) ready{Style.RESET_ALL}")

    def _handle_mcp_command(self, prompt: str) -> Optional[str]:
        """Handle MCP management commands."""
        parts = prompt.split()
        
        if len(parts) >= 2:
            if parts[1] == "list":
                return self._list_mcp_servers()
            elif parts[1] == "status":
                return self._mcp_status()
            elif parts[1] == "connect":
                return "Use: /mcp connect <server_name>\nServers: filesystem, git, memory"
        
        return None
    
    def _list_mcp_servers(self) -> str:
        """List connected MCP servers."""
        from colorama import Fore, Style
        
        if not hasattr(self, 'mcp_client') or not self.mcp_client:
            return f"{Fore.RED}No MCP client initialized{Style.RESET_ALL}"
        
        servers = self.mcp_client.list_servers()
        if not servers:
            return f"{Fore.YELLOW}No MCP servers connected{Style.RESET_ALL}"
        
        result = f"{Fore.CYAN}Connected MCP Servers:{Style.RESET_ALL}\n"
        for server in servers:
            tools = self.mcp_client.get_server_tools(server)
            result += f"  {Fore.YELLOW}{server}{Style.RESET_ALL}: {len(tools)} tools\n"
        
        return result
    
    def _mcp_status(self) -> str:
        """Show MCP connection status."""
        from colorama import Fore, Style
        
        if not hasattr(self, 'mcp_client') or not self.mcp_client:
            return f"{Fore.RED}MCP not initialized{Style.RESET_ALL}"
        
        servers = self.mcp_client.list_servers()
        total_tools = len(self.mcp_client.get_all_tools())
        
        return f"{Fore.GREEN}MCP Status:{Style.RESET_ALL}\n  Servers: {len(servers)}\n  Total tools: {total_tools}"


class MCPToolWrapper:
    """Wrapper to expose MCP tools as M.A.V.E.R.I.C.K tools."""
    
    def __init__(self, server_name: str, tool_name: str, description: str, 
                 input_schema: Dict[str, Any], mcp_client: MCPClient):
        self.server_name = server_name
        self.tool_name = tool_name
        self._description = description
        self.input_schema = input_schema
        self.mcp_client = mcp_client
        self.name = f"{server_name}_{tool_name}"
    
    @property
    def description(self) -> str:
        return self._description
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self._description,
                "parameters": self.input_schema or {"type": "object", "properties": {}}
            }
        }
    
    def _get_parameters_schema(self) -> Dict[str, Any]:
        return self.input_schema or {"type": "object", "properties": {}}
    
    async def execute(self, **kwargs):
        """Execute the MCP tool."""
        try:
            result = await self.mcp_client.call_tool(self.server_name, self.tool_name, kwargs)
            if isinstance(result, dict) and "error" in result:
                return ToolResult(success=False, result=None, error=result["error"])
            return ToolResult(success=True, result=result, error=None)
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    async def _cleanup(self):
        """Clean up resources."""
        if self.runner:
            await self.runner.close()
        if hasattr(self, 'mcp_client') and self.mcp_client:
            await self.mcp_client.disconnect_all()