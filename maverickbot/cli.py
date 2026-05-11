"""M.A.V.E.R.I.C.K v2.0 - AI agent with plugin & skill system."""
import argparse
import asyncio
import os
import sys
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Load .env file
from pathlib import Path
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

from loguru import logger
logger.disable("maverickbot")

from colorama import init, Fore, Style

init(autoreset=True)

from maverickbot.providers import ProviderRegistry
from maverickbot.agent import AgentRunner, ToolRegistry
from maverickbot.agent.tools import (
    ReadFileTool,
    WriteFileTool,
    AppendFileTool,
    DeleteFileTool,
    ListDirectoryTool,
    CopyFileTool,
    MoveFileTool,
    CreateDirectoryTool,
    FileExistsTool,
    GetFileInfoTool,
    ShellTool,
    SearchTool,
    UniversalReadTool,
    ConvertDataTool,
    CreateDataFileTool,
)
from maverickbot.core import Registry
from maverickbot.multiagent import MultiAgentOrchestrator


class MaverickCLI:
    """M.A.V.E.R.I.C.K v2.0 interactive CLI with plugin, skill & multi-agent support."""

    def __init__(self, args):
        self.args = args
        self.provider = None
        self.runner = None
        self.tool_registry = None
        self.registry = Registry()
        self.orchestrator = None
        self.history_path = os.path.join(os.path.expanduser("~"), ".maverickbot_history")

    async def initialize(self):
        logger.remove()
        logger.add(sys.stderr, level="ERROR")

        provider_config = self._get_provider_config()
        self.provider = ProviderRegistry.create(self.args.provider, **provider_config)

        self.tool_registry = ToolRegistry()
        self.tool_registry.register(ReadFileTool())
        self.tool_registry.register(WriteFileTool())
        self.tool_registry.register(AppendFileTool())
        self.tool_registry.register(DeleteFileTool())
        self.tool_registry.register(ListDirectoryTool())
        self.tool_registry.register(CopyFileTool())
        self.tool_registry.register(MoveFileTool())
        self.tool_registry.register(CreateDirectoryTool())
        self.tool_registry.register(FileExistsTool())
        self.tool_registry.register(GetFileInfoTool())
        self.tool_registry.register(ShellTool())
        self.tool_registry.register(SearchTool())
        self.tool_registry.register(UniversalReadTool())
        self.tool_registry.register(ConvertDataTool())
        self.tool_registry.register(CreateDataFileTool())

        self.runner = AgentRunner(
            provider=self.provider,
            tool_registry=self.tool_registry,
            system_prompt=self.args.system,
            fallback_providers=[self.provider],
            fallback_names=[self.args.provider],
        )

        if self.args.multi_agent:
            self.orchestrator = MultiAgentOrchestrator(
                provider=self.provider,
                tool_registry=self.tool_registry,
            )
            await self.orchestrator.initialize()
            print(f"{Fore.GREEN}Multi-agent system initialized!{Style.RESET_ALL}")
            agents = self.orchestrator.list_agents()
            for agent in agents:
                print(f"  - {agent['name']} ({agent['role']}): {agent['capabilities']}")

    def _get_provider_config(self):
        config = {"model": self.args.model}
        if self.args.provider == "lmstudio":
            config["base_url"] = self.args.lmurl
        elif self.args.provider == "nvidia":
            config["api_key"] = os.environ.get("NVIDIA_API_KEY") or getattr(self.args, 'nvidia_api_key', "") or ""
            config["base_url"] = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
        elif self.args.provider == "groq":
            config["api_key"] = os.environ.get("GROQ_API_KEY", "")
        return config

    async def run(self):
        self.registry.initialize()

        if self.args.list_plugins:
            self.list_plugins()
            return

        if self.args.list_skills:
            self.list_skills()
            return

        if self.args.reload:
            self.registry.reload()
            print(f"{Fore.GREEN}Plugins and skills reloaded!{Style.RESET_ALL}")
            return

        if self.args.list_models:
            await self.list_models()
            return

        if self.args.list_agents:
            await self.list_agents()
            return

        if self.args.interactive or self.args.prompt:
            await self.initialize()
            if self.args.prompt:
                response = await self.runner.chat(
                    self.args.prompt,
                    temperature=self.args.temperature,
                    max_tokens=self.args.max_tokens,
                )
                print(f"{Fore.GREEN}Assistant:{Style.RESET_ALL} {response}")
            else:
                await self.interactive_loop()
        else:
            print(f"{Fore.YELLOW}No prompt provided. Use --interactive or --prompt 'your message'{Style.RESET_ALL}")

    async def list_models(self):
        if not self.provider:
            await self.initialize()
        models = await self.provider.list_models()
        print(f"{Fore.CYAN}Available models:{Style.RESET_ALL}")
        for model in models:
            print(f"  - {model}")

    async def list_agents(self):
        """List agents in multi-agent system."""
        if not self.provider:
            logger.remove()
            logger.add(sys.stderr, level="ERROR")
            provider_config = self._get_provider_config()
            self.provider = ProviderRegistry.create(self.args.provider, **provider_config)
            
            self.tool_registry = ToolRegistry()
            self.tool_registry.register(ReadFileTool())
            self.tool_registry.register(WriteFileTool())
            self.tool_registry.register(AppendFileTool())
            self.tool_registry.register(DeleteFileTool())
            self.tool_registry.register(ListDirectoryTool())
            self.tool_registry.register(CopyFileTool())
            self.tool_registry.register(MoveFileTool())
            self.tool_registry.register(CreateDirectoryTool())
            self.tool_registry.register(FileExistsTool())
            self.tool_registry.register(GetFileInfoTool())
            self.tool_registry.register(ShellTool())
            self.tool_registry.register(SearchTool())
            self.tool_registry.register(UniversalReadTool())
            self.tool_registry.register(ConvertDataTool())
            self.tool_registry.register(CreateDataFileTool())
            
            self.orchestrator = MultiAgentOrchestrator(
                provider=self.provider,
                tool_registry=self.tool_registry,
            )
            await self.orchestrator.initialize()
        
        if self.orchestrator:
            agents = self.orchestrator.list_agents()
            print(f"{Fore.CYAN}=== Multi-Agent System ==={Style.RESET_ALL}")
            for agent in agents:
                print(f"  {Fore.YELLOW}{agent['name']}{Style.RESET_ALL} ({agent['role']})")
                print(f"      Capabilities: {agent['capabilities']}")
        else:
            print(f"{Fore.YELLOW}Multi-agent system not available.{Style.RESET_ALL}")

    def list_plugins(self):
        """List all available plugins."""
        print(f"{Fore.CYAN}=== Available Tools (Plugins) ==={Style.RESET_ALL}")
        tools = self.registry.list_tools()
        if tools:
            for tool in tools:
                print(f"  {Fore.YELLOW}{tool['name']}{Style.RESET_ALL} v{tool['version']} - {tool['description']}")
                print(f"      Author: {tool['author']}")
        else:
            print("  No custom tools found")

        print(f"\n{Fore.CYAN}=== Available Providers (Plugins) ==={Style.RESET_ALL}")
        providers = self.registry.list_providers()
        if providers:
            for provider in providers:
                print(f"  {Fore.YELLOW}{provider['name']}{Style.RESET_ALL} v{provider['version']} - {provider['description']}")
        else:
            print("  No custom providers found")

    def list_skills(self):
        """List all available skills."""
        print(f"{Fore.CYAN}=== Available Skills ==={Style.RESET_ALL}")
        skills = self.registry.list_skills()
        if skills:
            for skill in skills:
                print(f"  {Fore.YELLOW}{skill['name']}{Style.RESET_ALL} v{skill['version']}")
                print(f"      {skill['description']}")
                print(f"      Tools: {skill['tools']}")
        else:
            print("  No skills available")
        print(f"\n{Fore.CYAN}Usage:{Style.RESET_ALL} Activate a skill in interactive mode with /skill <name>")

    async def interactive_loop(self):
        print(f"{Fore.CYAN}=== M.A.V.E.R.I.C.K Interactive Mode ==={Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Provider:{Style.RESET_ALL} {self.args.provider}")
        print(f"{Fore.YELLOW}URL:{Style.RESET_ALL} {self.args.lmurl}")
        print(f"{Fore.YELLOW}Model:{Style.RESET_ALL} {self.args.model}")
        print(f"{Fore.YELLOW}Type {Fore.CYAN}help{Style.RESET_ALL} for commands, {Fore.CYAN}exit{Style.RESET_ALL} to quit.\n")

        while True:
            try:
                user_input = input(f"{Fore.BLUE}You{Style.RESET_ALL} > ").strip()
                if not user_input:
                    continue

                if user_input.lower() in ["exit", "quit", "q"]:
                    print(f"{Fore.YELLOW}Goodbye!{Style.RESET_ALL}")
                    break

                if user_input.lower() == "help":
                    self.print_help()
                    continue

                if user_input.lower() == "clear":
                    os.system("cls" if os.name == "nt" else "clear")
                    continue

                if user_input.lower() == "models":
                    await self.list_models()
                    continue

                if user_input.lower().startswith("/skill"):
                    parts = user_input.split()
                    if len(parts) >= 2:
                        skill_name = parts[1]
                        if self.registry.activate_skill(skill_name):
                            print(f"{Fore.GREEN}Skill activated: {skill_name}{Style.RESET_ALL}")
                            active = self.registry.get_active_skills()
                            print(f"  Active skills: {', '.join(active)}")
                        else:
                            print(f"{Fore.RED}Skill not found: {skill_name}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.YELLOW}Usage: /skill <name>{Style.RESET_ALL}")
                        print(f"  Active: {self.registry.get_active_skills()}")
                    continue

                if user_input.lower() == "skills":
                    self.list_skills()
                    continue

                if user_input.lower() == "plugins":
                    self.list_plugins()
                    continue

                if user_input.lower() == "agents":
                    if self.orchestrator:
                        agents = self.orchestrator.list_agents()
                        for agent in agents:
                            print(f"  {agent['name']} ({agent['role']}): {agent['capabilities']}")
                    else:
                        print(f"{Fore.YELLOW}Multi-agent not enabled. Use --multi-agent flag.{Style.RESET_ALL}")
                    continue

                if user_input.lower() == "reset":
                    self.runner.reset()
                    print(f"{Fore.YELLOW}Conversation reset.{Style.RESET_ALL}")
                    continue

                if user_input.startswith("run "):
                    cmd = user_input[4:]
                    result = await self.tool_registry.execute("shell", command=cmd)
                    print(f"{Fore.GREEN}Output:{Style.RESET_ALL} {result.result if result.success else result.error}\n")
                    continue

                if user_input.startswith("write "):
                    parts = user_input[6:].split(" ", 1)
                    if len(parts) >= 2:
                        file_path, content = parts[0], parts[1]
                        result = await self.tool_registry.execute("write_file", file_path=file_path, content=content)
                        print(f"{Fore.GREEN}{Style.RESET_ALL} {result.result if result.success else result.error}\n")
                    else:
                        print(f"{Fore.RED}Usage: write <file> <content>{Style.RESET_ALL}")
                    continue

                if user_input.startswith("read "):
                    file_path = user_input[5:].strip()
                    result = await self.tool_registry.execute("read_file", file_path=file_path)
                    print(f"{Fore.GREEN}Content:{Style.RESET_ALL}\n{result.result if result.success else result.error}\n")
                    continue

                print(f"{Fore.CYAN}Thinking...{Style.RESET_ALL}")
                
                if self.orchestrator:
                    result = await self.orchestrator.process(user_input)
                    if result.get("result", {}).get("final_result"):
                        response = result["result"]["final_result"]
                    else:
                        response = str(result.get("result", {}))
                else:
                    response = await self.runner.chat(
                        user_input,
                        temperature=self.args.temperature,
                        max_tokens=self.args.max_tokens,
                    )
                print(f"{Fore.GREEN}Assistant:{Style.RESET_ALL} {response}\n")

            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Interrupted. Type 'exit' to quit.{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")

    def print_help(self):
        print(f"""
{Fore.CYAN}M.A.V.E.R.I.C.K v2.0 Commands:{Style.RESET_ALL}
  {Fore.YELLOW}help{Style.RESET_ALL}     - Show this help message
  {Fore.YELLOW}models{Style.RESET_ALL}   - List available LLM models
  {Fore.YELLOW}plugins{Style.RESET_ALL}  - List available plugins (tools/providers)
  {Fore.YELLOW}skills{Style.RESET_ALL}   - List available skills
  {Fore.YELLOW}agents{Style.RESET_ALL}    - List multi-agent workers
  {Fore.YELLOW}clear{Style.RESET_ALL}    - Clear screen
  {Fore.YELLOW}reset{Style.RESET_ALL}    - Reset conversation
  {Fore.YELLOW}exit{Style.RESET_ALL}     - Exit interactive mode

{Fore.CYAN}Skill Commands (v2.0):{Style.RESET_ALL}
  {Fore.YELLOW}/skill <name>{Style.RESET_ALL}  - Activate a skill (e.g., /skill code_analyzer)
  {Fore.YELLOW}/skill{Style.RESET_ALL}        - Show active skills

{Fore.CYAN}Multi-Agent (v2.0):{Style.RESET_ALL}
  Start with: {Fore.YELLOW}--multi-agent{Style.RESET_ALL} flag
  Available workers: {Fore.YELLOW}researcher, coder, writer{Style.RESET_ALL}
  Supervisor auto-decomposes tasks and coordinates workers

{Fore.CYAN}Direct tool commands:{Style.RESET_ALL}
  {Fore.YELLOW}run <command>{Style.RESET_ALL}      - Execute shell command
  {Fore.YELLOW}write <path> <content>{Style.RESET_ALL} - Write to file
  {Fore.YELLOW}read <path>{Style.RESET_ALL}      - Read file

{Fore.CYAN}Example:{Style.RESET_ALL}
  {Fore.YELLOW}run dir{Style.RESET_ALL}
  {Fore.YELLOW}write test.txt Hello World{Style.RESET_ALL}
  {Fore.YELLOW}read test.txt{Style.RESET_ALL}
  {Fore.YELLOW}/skill code_analyzer{Style.RESET_ALL}
  {Fore.YELLOW}maverickbot -i --multi-agent{Style.RESET_ALL}
""")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="M.A.V.E.R.I.C.K - AI agent with tool execution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--provider",
        "-p",
        choices=["ollama", "lmstudio", "nvidia", "openai", "groq"],
        default="nvidia",
        help="LLM provider to use (default: nvidia)",
    )

    parser.add_argument(
        "--lmurl",
        default="http://127.0.0.1:1234",
        help="LM Studio server URL (default: http://127.0.0.1:1234)",
    )

    parser.add_argument(
        "--model",
        "-m",
        default=None,
        help="Model name (default: google/gemma-4-e2b)",
    )

    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Start interactive chat mode",
    )

    parser.add_argument(
        "--prompt",
        "-c",
        help="Single prompt to execute (non-interactive)",
    )

    parser.add_argument(
        "--list-models",
        "-l",
        action="store_true",
        help="List available models for the provider",
    )

    parser.add_argument(
        "--list-plugins",
        action="store_true",
        help="List available plugins (tools and providers)",
    )

    parser.add_argument(
        "--list-skills",
        action="store_true",
        help="List available skills",
    )

    parser.add_argument(
        "--reload",
        action="store_true",
        help="Reload plugins and skills",
    )

    parser.add_argument(
        "--multi-agent",
        "-ma",
        action="store_true",
        help="Enable multi-agent system with supervisor + workers",
    )

    parser.add_argument(
        "--list-agents",
        action="store_true",
        help="List available agents in multi-agent system",
    )

    parser.add_argument(
        "--temperature",
        "-t",
        type=float,
        default=0.7,
        help="Temperature for generation (default: 0.7)",
    )

    parser.add_argument(
        "--max-tokens",
        type=int,
        default=4096,
        help="Max tokens to generate (default: 4096)",
    )

    parser.add_argument(
        "--system",
        "-s",
        default="You are a helpful AI assistant with access to tools.",
        help="System prompt (default: helpful AI assistant with tools)",
    )

    args = parser.parse_args()

    if args.model is None:
        args.model = "meta/llama-3.1-70b-instruct"

    cli = MaverickCLI(args)
    asyncio.run(cli.run())


if __name__ == "__main__":
    main()