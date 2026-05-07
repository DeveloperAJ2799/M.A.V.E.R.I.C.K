"""Multi-agent orchestrator."""
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path
from loguru import logger
import yaml

from .base import BaseAgent, AgentConfig, AgentRole
from .supervisor import SupervisorAgent
from .worker import WorkerAgent
from .message_bus import MessageBus


class MultiAgentOrchestrator:
    """
    Orchestrates multiple agents with supervisor + worker pattern.
    """

    def __init__(
        self,
        provider,
        tool_registry,
        config_dir: Path = None,
    ):
        self.provider = provider
        self.tool_registry = tool_registry
        self.message_bus = MessageBus()
        
        self.agents: Dict[str, BaseAgent] = {}
        self.supervisor: Optional[SupervisorAgent] = None
        self.workers: Dict[str, WorkerAgent] = {}
        
        self.config_dir = config_dir or Path(__file__).parent / "config"

    async def initialize(self):
        """Initialize the orchestrator and all agents."""
        await self.message_bus.start()
        
        await self._load_agent_configs()
        
        logger.info(f"MultiAgentOrchestrator initialized with {len(self.agents)} agents")

    async def _load_agent_configs(self):
        """Load agent configurations from YAML files."""
        agent_configs = list(self.config_dir.glob("*.yaml"))
        
        if not agent_configs:
            self._create_default_config()
            agent_configs = list(self.config_dir.glob("*.yaml"))
        
        for config_file in agent_configs:
            try:
                await self._load_agent_from_config(config_file)
            except Exception as e:
                logger.warning(f"Failed to load agent config {config_file}: {e}")

    def _create_default_config(self):
        """Create default agent configuration."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        default_config = {
            "supervisor": {
                "name": "supervisor",
                "role": "supervisor",
                "system_prompt": "You are a task supervisor that breaks down complex tasks into subtasks and coordinates workers.",
                "max_iterations": 10,
                "timeout": 120,
                "capabilities": ["planning", "coordination", "synthesis"],
            },
            "workers": [
                {
                    "name": "researcher",
                    "role": "worker",
                    "system_prompt": "You are a research specialist. Search for information, analyze data, and provide findings.",
                    "capabilities": ["search", "analysis", "information_gathering"],
                    "tools": ["search_tool", "read_file"],
                },
                {
                    "name": "coder",
                    "role": "worker", 
                    "system_prompt": "You are a coding specialist. Write, review, and debug code.",
                    "capabilities": ["coding", "debugging", "code_review"],
                    "tools": ["read_file", "write_file", "shell"],
                },
                {
                    "name": "writer",
                    "role": "worker",
                    "system_prompt": "You are a writing specialist. Create clear, well-structured content.",
                    "capabilities": ["writing", "editing", "summarization"],
                    "tools": ["read_file", "write_file"],
                },
            ],
        }
        
        config_path = self.config_dir / "agents.yaml"
        with open(config_path, "w") as f:
            yaml.dump(default_config, f, default_flow_style=False)
        
        logger.info("Created default agent configuration")

    async def _load_agent_from_config(self, config_file: Path):
        """Load a single agent from config file."""
        with open(config_file, "r") as f:
            config_data = yaml.safe_load(f)
        
        supervisor_data = config_data.get("supervisor")
        if supervisor_data:
            await self._create_supervisor(supervisor_data)
        
        workers_data = config_data.get("workers", [])
        for worker_data in workers_data:
            await self._create_worker(worker_data)

    async def _create_supervisor(self, config_data: Dict):
        """Create a supervisor agent."""
        config = AgentConfig(
            name=config_data.get("name", "supervisor"),
            role=AgentRole.SUPERVISOR,
            system_prompt=config_data.get("system_prompt", ""),
            model=config_data.get("model"),
            max_iterations=config_data.get("max_iterations", 10),
            timeout=config_data.get("timeout", 120),
            capabilities=config_data.get("capabilities", []),
            tools=config_data.get("tools", []),
        )
        
        supervisor = SupervisorAgent(
            config=config,
            provider=self.provider,
            tool_registry=self.tool_registry,
            message_bus=self.message_bus,
            worker_registry=self.workers,
        )
        
        await supervisor.initialize()
        await supervisor.activate()
        
        self.supervisor = supervisor
        self.agents[config.name] = supervisor
        logger.info(f"Created supervisor: {config.name}")

    async def _create_worker(self, config_data: Dict):
        """Create a worker agent."""
        config = AgentConfig(
            name=config_data.get("name", "worker"),
            role=AgentRole.WORKER,
            system_prompt=config_data.get("system_prompt", ""),
            model=config_data.get("model"),
            max_iterations=config_data.get("max_iterations", 10),
            timeout=config_data.get("timeout", 120),
            capabilities=config_data.get("capabilities", []),
            tools=config_data.get("tools", []),
        )
        
        worker = WorkerAgent(
            config=config,
            provider=self.provider,
            tool_registry=self.tool_registry,
            message_bus=self.message_bus,
        )
        
        await worker.initialize()
        await worker.activate()
        
        self.workers[config.name] = worker
        self.agents[config.name] = worker
        logger.info(f"Created worker: {config.name}")

    async def process(self, task: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process a task through the multi-agent system."""
        if context is None:
            context = {}
        
        if not self.supervisor:
            logger.warning("No supervisor configured, using direct execution")
            return await self._direct_execute(task, context)
        
        result = await self.supervisor.process(task, context)
        
        return {
            "status": "success",
            "task": task,
            "result": result,
            "agents_used": list(self.agents.keys()),
        }

    async def _direct_execute(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Direct execution without supervisor."""
        for name, agent in self.workers.items():
            result = await agent.process(task, context)
            return result
        
        return {"status": "no_agents", "error": "No worker agents available"}

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get an agent by name."""
        return self.agents.get(name)

    def list_agents(self) -> List[Dict[str, str]]:
        """List all agents."""
        return [
            {
                "name": name,
                "role": agent.role.value,
                "capabilities": ", ".join(agent.config.capabilities or []),
            }
            for name, agent in self.agents.items()
        ]

    async def shutdown(self):
        """Shutdown all agents and message bus."""
        for agent in self.agents.values():
            await agent.deactivate()
        
        await self.message_bus.stop()
        logger.info("MultiAgentOrchestrator shutdown complete")