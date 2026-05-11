"""Thinking Agent - Self-critiquing agent with planning capabilities."""

import asyncio
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger

from .tools.registry import ToolRegistry


class ExecutionMode(Enum):
    THINK_ONLY = "think_only"
    PLAN = "plan"
    EXECUTE = "execute"


@dataclass
class ThoughtStep:
    step_type: str
    content: str
    confidence: float = 1.0
    concerns: List[str] = field(default_factory=list)
    reasoning: str = ""


@dataclass 
class AgentPlan:
    mode: ExecutionMode
    action_type: str
    understanding: str
    steps: List[ThoughtStep]
    tool_to_use: str
    arguments: Dict[str, Any]
    output_path: Optional[str] = None
    needs_clarification: bool = False
    clarification_questions: List[str] = field(default_factory=list)


class ThinkingAgent:
    def __init__(self, tool_registry: ToolRegistry, llm_provider=None):
        self.tool_registry = tool_registry
        self.llm_provider = llm_provider
        self.think_history: List[ThoughtStep] = []
        self.execution_history: List[Dict] = []
    
    async def process(self, user_input: str) -> Tuple[str, AgentPlan]:
        mode = self._detect_mode(user_input)
        plan = await self._think(user_input, mode)
        
        if mode == ExecutionMode.PLAN:
            plan_text = self._format_plan(plan)
            return plan_text, plan
        
        if mode == ExecutionMode.THINK_ONLY:
            think_text = self._format_thinking(plan.steps)
            return think_text, plan
        
        if mode == ExecutionMode.EXECUTE:
            return await self._execute_with_reflection(plan)
        
        return "", plan
    
    def _detect_mode(self, user_input: str) -> ExecutionMode:
        text_lower = user_input.lower().strip()
        if text_lower.startswith("/plan") or "show your plan" in text_lower:
            return ExecutionMode.PLAN
        if text_lower.startswith("/think") or text_lower.startswith("analyze"):
            return ExecutionMode.THINK_ONLY
        return ExecutionMode.EXECUTE
    
    async def _think(self, user_input: str, mode: ExecutionMode) -> AgentPlan:
        tool_schemas = self.tool_registry.get_schemas()
        
        thinking_prompt = f"""Create a PDF with content about: {user_input}

Requirements:
- Generate detailed content, at least 300+ words
- If multiple topics, use separate sections with ## headings
- Output filename should end in .pdf

Return ONLY this JSON format:
{{"tool_name": "create_pdf", "arguments": {{"content": "WRITE CONTENT HERE", "output": "filename.pdf"}}}}
"""
        
        if self.llm_provider:
            try:
                spinner = _ThinkingSpinner()
                spinner.start()
                response = await self.llm_provider.chat(
                    messages=[{"role": "user", "content": thinking_prompt}],
                    max_tokens=4000
                )
                spinner.stop()
                return self._parse_thinking_response(response.content or "", user_input)
            except Exception as e:
                logger.error(f"Thinking failed: {e}")
        
        return self._simple_parse(user_input, tool_schemas)
    
    def _parse_thinking_response(self, response: str, user_input: str) -> AgentPlan:
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                json_str = json_match.group().strip()
                data = json.loads(json_str)
                
                return AgentPlan(
                    mode=ExecutionMode.EXECUTE,
                    action_type=data.get("action_type", "create_pdf"),
                    understanding=user_input,
                    steps=[],
                    tool_to_use=data.get("tool_name", "create_pdf"),
                    arguments=data.get("arguments", {}),
                    output_path=data.get("output_path")
                )
        except Exception as e:
            logger.warning(f"Failed to parse thinking response: {e}")
        
        return self._simple_parse(user_input, self.tool_registry.get_schemas())
    
    def _simple_parse(self, user_input: str, schemas: List[Dict]) -> AgentPlan:
        text_lower = user_input.lower()
        
        if any(w in text_lower for w in ["pdf", "document", "file"]):
            if any(w in text_lower for w in ["make", "create", "generate", "new"]):
                topic = ""
                for trigger in [" on ", " about ", " with "]:
                    if trigger in text_lower:
                        parts = text_lower.split(trigger)
                        if len(parts) > 1:
                            topic = parts[1].strip()
                            for end in ["100+ words", "words", "pdf", "file"]:
                                if topic.endswith(end):
                                    topic = topic[:-len(end)].strip()
                            break
                
                import re as re_module
                quoted = re_module.findall(r'"([^"]+)"', user_input)
                content = quoted[0] if quoted else f"Content about {topic or user_input}"
                
                return AgentPlan(
                    mode=ExecutionMode.EXECUTE,
                    action_type="create_pdf",
                    understanding=user_input,
                    steps=[],
                    tool_to_use="create_pdf",
                    arguments={"content": content, "output": "document.pdf"}
                )
        
        return AgentPlan(
            mode=ExecutionMode.EXECUTE,
            action_type="chat",
            understanding=user_input,
            steps=[],
            tool_to_use="chat",
            arguments={}
        )
    
    async def _execute_with_reflection(self, plan: AgentPlan) -> Tuple[str, AgentPlan]:
        tool_name = plan.tool_to_use
        args = plan.arguments.copy()
        
        if not tool_name or tool_name == "chat":
            return "I don't understand. Please try again.", plan
        
        try:
            spinner = _ProcessBar(tool_name)
            spinner.start()
            result = await self.tool_registry.execute(tool_name, **args)
            spinner.stop(success=result.success)
            
            if result.success:
                return result.result, plan
            else:
                return f"Error: {result.error}", plan
        except Exception as e:
            return f"Execution failed: {str(e)}", plan
    
    def _format_plan(self, plan: AgentPlan) -> str:
        lines = ["📋 PLAN:", "", f"Action: {plan.action_type}", f"Tool: {plan.tool_to_use}"]
        if plan.arguments:
            lines.append(f"Arguments: {json.dumps(plan.arguments, indent=2)}")
        return "\n".join(lines)
    
    def _format_thinking(self, steps: List[ThoughtStep]) -> str:
        return "🧠 Analysis complete"


import threading
import time


class _ThinkingSpinner:
    FRAMES = ['|', '/', '-', '\\']
    
    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None
        self._frame = 0
    
    def _spin(self):
        import sys
        colors = {'cyan': '\033[36m', 'green': '\033[32m', 'magenta': '\033[35m', 'yellow': '\033[33m', 'blue': '\033[34m', 'light_magenta': '\033[95m', 'reset': '\033[0m'}
        color_names = ['cyan', 'green', 'magenta', 'yellow', 'blue', 'light_magenta']
        idx = 0
        
        while not self._stop_event.is_set():
            color = colors[color_names[idx % len(color_names)]]
            reset = colors['reset']
            frame = self.FRAMES[self._frame % len(self.FRAMES)]
            sys.stdout.write(f'\r{color}Thinking{reset}... {frame}')
            sys.stdout.flush()
            self._frame += 1
            idx += 1
            time.sleep(0.1)
    
    def start(self):
        self._stop_event.clear()
        self._frame = 0
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
    
    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=0.3)
        import sys
        sys.stdout.write('\r' + ' ' * 25 + '\r')
        sys.stdout.flush()


class _ProcessBar:
    FRAMES = ['    ', '=>  ', '===>', '====', '===>', '=>> ']
    
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self._stop_event = threading.Event()
        self._thread = None
        self._frame = 0
    
    def _animate(self):
        import sys
        colors = {'cyan': '\033[36m', 'green': '\033[32m', 'magenta': '\033[35m', 'yellow': '\033[33m', 'blue': '\033[34m', 'light_magenta': '\033[95m', 'reset': '\033[0m'}
        color_names = ['cyan', 'green', 'magenta', 'yellow', 'blue', 'light_magenta']
        idx = 0
        
        while not self._stop_event.is_set():
            color = colors[color_names[idx % len(color_names)]]
            reset = colors['reset']
            frame = self.FRAMES[self._frame % len(self.FRAMES)]
            sys.stdout.write(f'\r{color}Running {self.tool_name}{reset}: [{frame}]')
            sys.stdout.flush()
            self._frame += 1
            idx += 1
            time.sleep(0.12)
    
    def start(self):
        self._stop_event.clear()
        self._frame = 0
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()
    
    def stop(self, success: bool = True):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=0.3)
        import sys
        sys.stdout.write('\r' + ' ' * 40 + '\r')
        sys.stdout.flush()
        
        colors = {'cyan': '\033[36m', 'green': '\033[32m', 'magenta': '\033[35m', 'reset': '\033[0m'}
        color = colors['green'] if success else colors['magenta']
        status = "Done" if success else "Failed"
        print(f"{colors['cyan']}→ {self.tool_name}: {color}{status}{colors['reset']}")