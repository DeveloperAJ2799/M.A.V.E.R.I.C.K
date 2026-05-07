"""Supervisor agent for task decomposition."""
import json
import asyncio
from typing import Dict, List, Any, Optional
from loguru import logger

from .base import BaseAgent, AgentConfig, AgentRole
from .message_bus import MessageBus, AgentMessage, MessageType


class SupervisorAgent(BaseAgent):
    """
    Supervisor agent that decomposes complex tasks into subtasks
    and coordinates worker agents.
    """

    def __init__(
        self,
        config: AgentConfig,
        provider,
        tool_registry,
        message_bus: MessageBus,
        worker_registry: Dict[str, BaseAgent],
    ):
        super().__init__(config, provider, tool_registry, message_bus)
        self.worker_registry = worker_registry

    async def initialize(self):
        """Initialize the supervisor."""
        logger.info(f"Initializing SupervisorAgent: {self.name}")

    async def process(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main supervisor process:
        1. Analyze task
        2. Decompose into subtasks
        3. Assign to workers
        4. Synthesize results
        """
        logger.info(f"Supervisor {self.name} processing task")
        
        task_str = task if isinstance(task, str) else str(task)
        
        plan = await self._create_plan(task_str, context)
        
        if not plan.get("subtasks"):
            return await self._handle_simple_task(task_str, context)
        
        results = await self._execute_subtasks(plan["subtasks"], context)
        
        final_result = await self._synthesize_results(task_str, results, context)
        
        return {
            "status": "completed",
            "plan": plan,
            "subtask_results": results,
            "final_result": final_result,
        }

    async def _create_plan(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create a plan by decomposing the task."""
        system_msg = {
            "role": "system",
            "content": f"""{self.config.system_prompt}

You are a task planning expert. Analyze the user's request and create a plan.
Break down complex tasks into smaller, independent subtasks that can be executed in parallel.

Available workers and their capabilities:
{self._get_worker_descriptions()}

Respond with a JSON plan in this format:
{{
    "task_summary": "Brief summary of what needs to be done",
    "subtasks": [
        {{"id": 1, "description": "subtask description", "worker": "worker_name", "depends_on": []}},
        ...
    ],
    "can_parallelize": [1, 2, 3]  # IDs of tasks that can run in parallel
}}

If the task is simple enough to handle directly, return subtasks: [].
"""
        }
        
        messages = [
            system_msg,
            {"role": "user", "content": f"Task: {task}\n\nContext: {json.dumps(context, indent=2)}"}
        ]
        
        try:
            response = await self.chat(messages, tools=False)
            plan = self._parse_plan(response)
            logger.info(f"Created plan with {len(plan.get('subtasks', []))} subtasks")
            return plan
        except Exception as e:
            logger.error(f"Failed to create plan: {e}")
            return {"task_summary": task, "subtasks": [], "can_parallelize": []}

    def _get_worker_descriptions(self) -> str:
        """Get descriptions of available workers."""
        descriptions = []
        for name, worker in self.worker_registry.items():
            caps = worker.config.capabilities or []
            tools = worker.config.tools or []
            descriptions.append(f"- {name}: capabilities={caps}, tools={tools}")
        return "\n".join(descriptions)

    def _parse_plan(self, response: str) -> Dict[str, Any]:
        """Parse the plan from LLM response."""
        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                plan = json.loads(response[json_start:json_end])
                return plan
        except json.JSONDecodeError:
            pass
        
        return {"task_summary": response, "subtasks": [], "can_parallelize": []}

    async def _execute_subtasks(self, subtasks: List[Dict[str, Any]], context: Dict[str, Any]) -> Dict[int, Any]:
        """Execute subtasks, optionally in parallel."""
        results = {}
        
        can_parallel = subtasks[0].get("can_parallelize", []) if subtasks else []
        serial_tasks = [s for s in subtasks if s.get("id") not in can_parallel]
        parallel_tasks = [s for s in subtasks if s.get("id") in can_parallel]
        
        for subtask in serial_tasks:
            result = await self._execute_single_subtask(subtask, context)
            results[subtask["id"]] = result
        
        if parallel_tasks:
            parallel_results = await asyncio.gather(
                *[self._execute_single_subtask(st, context) for st in parallel_tasks]
            )
            for st, result in zip(parallel_tasks, parallel_results):
                results[st["id"]] = result
        
        return results

    async def _execute_single_subtask(self, subtask: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """Execute a single subtask via worker agent."""
        worker_name = subtask.get("worker")
        worker = self.worker_registry.get(worker_name)
        
        if not worker:
            logger.warning(f"Worker {worker_name} not found")
            return {"error": f"Worker {worker_name} not found"}
        
        if not worker.is_active():
            await worker.activate()
        
        result = await worker.process(subtask["description"], context)
        return result

    async def _synthesize_results(self, original_task: str, results: Dict[int, Any], context: Dict[str, Any]) -> str:
        """Synthesize results from all subtasks into final response."""
        system_msg = {
            "role": "system",
            "content": f"""{self.config.system_prompt}

You are responsible for synthesizing results from multiple subtasks into a coherent response.
The original task was: {original_task}

Subtask results:
{json.dumps(results, indent=2)}

Provide a clear, concise synthesis of all the results.
"""
        }
        
        messages = [system_msg]
        
        try:
            response = await self.chat(messages, tools=False)
            return response
        except Exception as e:
            logger.error(f"Failed to synthesize results: {e}")
            return f"Completed {len(results)} subtasks. Results: {results}"

    async def _handle_simple_task(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a simple task directly without decomposition."""
        result = await self.chat(
            [{"role": "user", "content": task}],
            tools=True
        )
        return {
            "status": "completed",
            "result": result,
        }

    async def _on_message(self, message: AgentMessage):
        """Handle incoming messages from other agents."""
        if message.type == MessageType.TASK:
            result = await self.process(message.payload.get("task"), message.payload.get("context", {}))
            response_msg = AgentMessage(
                id=str(message.id),
                sender=self.name,
                receiver=message.sender,
                type=MessageType.RESULT,
                payload={"result": result},
                correlation_id=message.id,
            )
            await self.message_bus.publish(response_msg)