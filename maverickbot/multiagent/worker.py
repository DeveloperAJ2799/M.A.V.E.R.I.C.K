"""Worker agent for specialized task execution."""
import json
from typing import Dict, List, Any, Optional
from loguru import logger

from .base import BaseAgent, AgentConfig, AgentRole
from .message_bus import AgentMessage, MessageType


class WorkerAgent(BaseAgent):
    """
    Worker agent that executes specific tasks using its specialized
    capabilities and tools.
    """

    def __init__(
        self,
        config: AgentConfig,
        provider,
        tool_registry,
        message_bus=None,
    ):
        super().__init__(config, provider, tool_registry, message_bus)
        self.execution_history = []

    async def initialize(self):
        """Initialize the worker."""
        logger.info(f"Initializing WorkerAgent: {self.name} (role: {self.config.role})")

    async def process(self, task: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a task using the worker's specialized capabilities.
        """
        logger.info(f"Worker {self.name} processing task")
        
        task_str = task if isinstance(task, str) else str(task)
        
        result = await self._execute_task(task_str, context)
        
        self.execution_history.append({
            "task": task_str,
            "result": result,
        })
        
        return result

    async def _execute_task(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the task with available tools and LLM."""
        
        if not self.config.tools:
            return await self._execute_without_tools(task, context)
        
        return await self._execute_with_tools(task, context)

    async def _execute_without_tools(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute task using only LLM reasoning."""
        system_msg = {
            "role": "system",
            "content": f"""{self.config.system_prompt}

You are a specialized worker. Execute the given task using your expertise.

Your capabilities: {self.config.capabilities}
Your role: {self.config.role.value}

Provide a thorough and accurate response.
"""
        }
        
        messages = [
            system_msg,
            {"role": "user", "content": f"Task: {task}\n\nContext: {json.dumps(context, indent=2)}"}
        ]
        
        try:
            response = await self.chat(messages, tools=False)
            return {
                "status": "completed",
                "result": response,
                "worker": self.name,
            }
        except Exception as e:
            logger.error(f"Worker {self.name} execution failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "worker": self.name,
            }

    async def _execute_with_tools(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute task with tools."""
        available_tools = [t for t in self.config.tools if self.tool_registry.get(t)]
        
        system_msg = {
            "role": "system",
            "content": f"""{self.config.system_prompt}

You are a specialized worker with access to tools.

Your capabilities: {self.config.capabilities}
Available tools: {available_tools}

Execute the task efficiently. If tools are needed, use them. Otherwise, provide a direct response.
"""
        }
        
        messages = [
            system_msg,
            {"role": "user", "content": f"Task: {task}\n\nContext: {json.dumps(context, indent=2)}"}
        ]
        
        iteration = 0
        max_iterations = self.config.max_iterations
        
        while iteration < max_iterations:
            response = await self.provider.chat(
                messages=messages,
                tools=[self.tool_registry.get_schemas()[0]] if available_tools else None,
            )
            
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    result = await self._execute_tool_call(tool_call, messages)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.get("id"),
                        "content": result.result if result.success else f"Error: {result.error}",
                    })
            else:
                return {
                    "status": "completed",
                    "result": response.content,
                    "worker": self.name,
                    "iterations": iteration + 1,
                }
            
            iteration += 1
        
        return {
            "status": "max_iterations",
            "result": "Reached maximum iterations",
            "worker": self.name,
        }

    async def _execute_tool_call(self, tool_call, messages: List[Dict]) -> Any:
        """Execute a tool call and add result to messages."""
        func = tool_call.get("function", {})
        tool_name = func.get("name")
        arguments = func.get("arguments", "{}")
        
        try:
            if isinstance(arguments, str):
                args = json.loads(arguments)
            else:
                args = arguments
        except json.JSONDecodeError:
            args = {"input": str(arguments)}
        
        result = await self.tool_registry.execute(tool_name, **args)
        return result

    async def _on_message(self, message: AgentMessage):
        """Handle incoming task messages."""
        if message.type == MessageType.TASK:
            task = message.payload.get("task")
            context = message.payload.get("context", {})
            
            result = await self.process(task, context)
            
            response_msg = AgentMessage(
                id=str(message.id),
                sender=self.name,
                receiver=message.sender,
                type=MessageType.RESULT,
                payload={"result": result},
                correlation_id=message.id,
            )
            
            if self.message_bus:
                await self.message_bus.publish(response_msg)