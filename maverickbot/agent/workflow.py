"""Workflow planner for automatic task execution."""
import json
import asyncio
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from loguru import logger


class WorkflowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    step_id: int
    tool_name: str
    arguments: Dict[str, Any]
    description: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None


@dataclass
class Workflow:
    """A multi-step workflow to accomplish a task."""
    goal: str
    steps: List[WorkflowStep]
    current_step: int = 0
    status: WorkflowStatus = WorkflowStatus.PENDING


class WorkflowPlanner:
    """Plans and executes workflows automatically."""

    WORKFLOW_PROMPT = """You are a workflow planner. Analyze the user's request and create a step-by-step plan.

Available tools:
{tool_list}

IMPORTANT - PDF Workflow Guidelines:
- create_pdf has a "source_pdf" parameter - use this to read from existing PDFs directly
- Use create_pdf source_pdf parameter instead of manually passing content
- Example: {{"tool_name": "create_pdf", "arguments": {{"source_pdf": "input.pdf", "output": "output.pdf"}}}} 

Your task:
1. Analyze what the user wants to accomplish
2. Determine which tools are needed
3. Create an ordered list of steps
4. For each step, specify the tool and required arguments

Respond with ONLY a JSON workflow plan in this format:
{{
    "goal": "What the user wants to achieve",
    "steps": [
        {{
            "step_id": 1,
            "tool_name": "tool_name",
            "arguments": {{"param": "value"}},
            "description": "What this step does"
        }}
    ]
}}

If no tools are needed, respond with:
{{"goal": "...", "steps": []}}

Be practical and break down complex tasks into manageable steps."""

    def __init__(self, tool_registry, provider):
        self.tool_registry = tool_registry
        self.provider = provider

    async def plan(self, user_request: str) -> Workflow:
        """Create a workflow plan for the user request."""
        tool_schemas = self.tool_registry.get_schemas()
        tool_list = "\n".join([
            f"- {s['function']['name']}: {s['function']['description']}"
            for s in tool_schemas
        ])
        
        prompt = self.WORKFLOW_PROMPT.format(tool_list=tool_list)
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_request}
        ]
        
        try:
            response = await self.provider.chat(messages=messages, max_tokens=4096)
            content = response.content or ""
            
            # Parse JSON from response
            workflow_data = self._extract_json(content)
            
            if workflow_data and "steps" in workflow_data:
                steps = []
                for step_data in workflow_data["steps"]:
                    steps.append(WorkflowStep(
                        step_id=step_data.get("step_id", 0),
                        tool_name=step_data.get("tool_name", ""),
                        arguments=step_data.get("arguments", {}),
                        description=step_data.get("description", "")
                    ))
                
                return Workflow(
                    goal=workflow_data.get("goal", user_request),
                    steps=steps
                )
            else:
                return Workflow(goal=user_request, steps=[])
                
        except Exception as e:
            logger.error(f"Workflow planning failed: {e}")
            return Workflow(goal=user_request, steps=[])

    def _extract_json(self, content: str) -> Optional[Dict]:
        """Extract JSON from response content with multiple fallback strategies."""
        content = content.strip()
        
        # 1. Try direct JSON parse
        try:
            return json.loads(content)
        except:
            pass
        
        # 2. Try to find JSON in markdown code blocks
        import re
        code_block_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', content)
        if code_block_match:
            try:
                return json.loads(code_block_match.group(1).strip())
            except:
                pass
        
        # 3. Try to find anything that looks like a JSON object with "steps"
        # Find the first { and the last } that surround "steps"
        try:
            steps_idx = content.find('"steps"')
            if steps_idx != -1:
                start_idx = content.rfind('{', 0, steps_idx)
                if start_idx != -1:
                    # Try to find matching closing brace
                    depth = 0
                    for i in range(start_idx, len(content)):
                        if content[i] == '{':
                            depth += 1
                        elif content[i] == '}':
                            depth -= 1
                            if depth == 0:
                                try:
                                    return json.loads(content[start_idx:i+1])
                                except:
                                    break
        except:
            pass
        
        return None

    async def execute_workflow(self, workflow: Workflow, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Execute a workflow step by step with improved context passing."""
        results = []
        context = {}  # Shared context between steps
        
        for i, step in enumerate(workflow.steps):
            if step.status == WorkflowStatus.COMPLETED:
                continue
                
            step.status = WorkflowStatus.RUNNING
            workflow.current_step = i
            
            if progress_callback:
                progress_callback(f"Step {i+1}/{len(workflow.steps)}: {step.description}")
            
            try:
                # Update arguments with context from previous steps
                # Only inject if the parameter is empty/missing
                args = step.arguments.copy()
                for key, value in context.items():
                    if key in args and not args[key]:
                        args[key] = value
                    # Special handling for "content" or "file" if not specified
                    if "content" in step.tool_name and "content" not in args and "content" in context:
                        args["content"] = context["content"]
                    if "pdf" in step.tool_name and ("source" in step.tool_name or "read" in step.tool_name) and "file" not in args and "last_output" in context:
                        args["file"] = context["last_output"]
                
                result = await self.tool_registry.execute(
                    step.tool_name, 
                    **args
                )
                
                if result.success:
                    step.status = WorkflowStatus.COMPLETED
                    step.result = result.result
                    
                    # More robust context extraction
                    res_str = str(result.result)
                    res_lower = res_str.lower()
                    
                    # 1. If it looks like a path, store it
                    import re
                    path_match = re.search(r'(?:Created|Saved|at|path)[:\s]+([^\s]+\.(?:pdf|docx|txt|xlsx|csv|pptx|png|jpg|mp3))', res_str)
                    if path_match:
                        context["last_output"] = path_match.group(1).strip()
                    elif ".pdf" in res_lower or ".txt" in res_lower or ".docx" in res_lower:
                        # Fallback: look for any path-like string
                        words = res_str.split()
                        for word in reversed(words):
                            if "." in word and len(word) > 4:
                                context["last_output"] = word.strip('.,()[]{}"\'')
                                break
                    
                    # 2. If it's a large text result, store it as content
                    if len(res_str) > 100 or "content" in res_lower or "text" in res_lower:
                        context["content"] = res_str
                        
                else:
                    step.status = WorkflowStatus.FAILED
                    step.error = result.error
                    return {
                        "success": False,
                        "step": i + 1,
                        "error": result.error,
                        "completed_steps": [s for s in workflow.steps if s.status == WorkflowStatus.COMPLETED]
                    }
                    
            except Exception as e:
                step.status = WorkflowStatus.FAILED
                step.error = str(e)
                return {
                    "success": False,
                    "step": i + 1,
                    "error": str(e),
                    "completed_steps": [s for s in workflow.steps if s.status == WorkflowStatus.COMPLETED]
                }
            
            results.append({
                "step": i + 1,
                "tool": step.tool_name,
                "result": step.result
            })
        
        workflow.status = WorkflowStatus.COMPLETED
        
        return {
            "success": True,
            "goal": workflow.goal,
            "steps_completed": len(workflow.steps),
            "results": results,
            "final_context": context
        }


class AutoExecuteLoop:
    """Agent loop with automatic workflow planning and execution."""

    def __init__(self, agent_loop: Any):
        self.agent_loop = agent_loop
        self.planner = WorkflowPlanner(agent_loop.tool_registry, agent_loop.provider)
        self.auto_planning_enabled = True

    async def process_message(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = None,
    ) -> str:
        """Process message with automatic workflow detection."""
        
        # Check if user wants to skip workflow planning
        last_message = messages[-1]["content"] if messages else ""
        
        if last_message.startswith("!noworkflow"):
            # Skip workflow planning
            messages[-1]["content"] = last_message.replace("!noworkflow", "").strip()
            return await self.agent_loop.process_message(messages, system_prompt)
        
        if last_message.startswith("!plan"):
            # Show workflow plan only, don't execute
            return await self._show_plan_only(messages)
        
        # Normal processing with automatic planning
        return await self._auto_process(messages, system_prompt)

    async def _show_plan_only(self, messages: List[Dict[str, str]]) -> str:
        """Show workflow plan without executing."""
        user_request = messages[-1]["content"].replace("!plan", "").strip()
        
        workflow = await self.planner.plan(user_request)
        
        if not workflow.steps:
            return "No tools needed for this task. I'll answer directly."
        
        plan_text = f"## Workflow Plan for: {workflow.goal}\n\n"
        for step in workflow.steps:
            plan_text += f"**Step {step.step_id}:** {step.description}\n"
            plan_text += f"→ Tool: `{step.tool_name}`\n"
            plan_text += f"→ Args: `{json.dumps(step.arguments)}`\n\n"
        
        plan_text += "\n*To execute this plan, remove the `!plan` prefix and ask again.*"
        
        return plan_text

    async def _auto_process(self, messages: List[Dict[str, str]], system_prompt: str = None) -> str:
        """Automatically detect if workflow is needed and execute."""
        user_request = messages[-1]["content"]
        
        # First, create a workflow plan
        workflow = await self.planner.plan(user_request)
        
        if not workflow.steps:
            # No tools needed, process normally
            messages.append({
                "role": "system", 
                "content": "No tools required for this task. Provide a direct response."
            })
            return await self.agent_loop.process_message(messages, system_prompt)
        
        # Show the plan and ask if user wants to proceed
        print(f"\n📋 Detected workflow with {len(workflow.steps)} steps")
        for step in workflow.steps:
            print(f"   {step.step_id}. {step.description}")
        print()
        
        # Execute the workflow automatically
        result = await self.planner.execute_workflow(workflow)
        
        if result["success"]:
            # Get final context and find output file
            final_context = result.get("final_context", {})
            final_result = result.get("results", [])[-1] if result.get("results") else {}
            tool_result = final_result.get("result", "")
            
            # Extract output path from tool result
            output_path = ""
            if tool_result:
                import re
                path_match = re.search(r'(?:Created|Saved|at)[:\s]+([^\s]+\.pdf)', str(tool_result))
                if path_match:
                    output_path = path_match.group(1)
            
            # Add results to messages for final response
            tool_results = []
            for r in result.get("results", []):
                tool_results.append(f"Step {r['step']} ({r['tool']}): {r['result']}")
            
            messages.append({
                "role": "system",
                "content": f"Workflow completed. Results:\n" + "\n".join(tool_results)
            })
            
            # Get final response summarizing the work done
            summary_prompt = f"""Workflow completed successfully: {workflow.goal}

Results:
{chr(10).join(tool_results)}

Output file: {output_path if output_path else 'Check above for file location'}

Please confirm the file was created and tell the user the exact file path."""
            
            messages.append({
                "role": "user",
                "content": summary_prompt
            })
            
            return await self.agent_loop.process_message(messages, system_prompt)
        else:
            return f"Workflow failed at step {result['step']}: {result['error']}"


def create_auto_execute_loop(agent_loop) -> AutoExecuteLoop:
    """Create an auto-executing loop wrapper."""
    return AutoExecuteLoop(agent_loop)
