"""Planning tool for complex multi-step tasks."""
import json
from typing import Any, Dict
from .base import Tool, ToolResult


class PlanTool(Tool):
    """Tool for creating and managing task plans."""

    def __init__(self):
        super().__init__(
            name="plan",
            description="Create a structured plan for complex tasks. Returns a numbered list of steps to complete.",
        )

    async def execute(
        self,
        goal: str,
        constraints: str = "",
        **kwargs
    ) -> ToolResult:
        try:
            plan = f"""# Plan: {goal}

## Steps

1. **Understand the requirement**
   - Analyze the goal: {goal}
   - Identify key components needed

2. **Break down into tasks**
   - List all necessary steps
   - Order dependencies

3. **Execute steps**
   - Complete each step
   - Verify results

4. **Review and refine**
   - Check against goal
   - Fix any issues

## Constraints
{constraints if constraints else "- No specific constraints"}

---

*This is a planning scaffold. Execute each step using available tools.*
"""
            return ToolResult(success=True, result=plan)
        
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "The main goal or objective to plan for",
                },
                "constraints": {
                    "type": "string",
                    "description": "Any constraints or requirements to consider",
                },
            },
            "required": ["goal"],
        }


class TodoListTool(Tool):
    """Tool for tracking tasks and todos."""

    def __init__(self):
        super().__init__(
            name="todo",
            description="Track tasks and TODOs. Can add, list, complete, or remove tasks.",
        )
        self._tasks: Dict[str, list] = {}

    async def execute(
        self,
        action: str = "list",
        task: str = "",
        list_name: str = "default",
        **kwargs
    ) -> ToolResult:
        try:
            if list_name not in self._tasks:
                self._tasks[list_name] = []
            
            if action == "add":
                if task:
                    self._tasks[list_name].append({"text": task, "done": False})
                    return ToolResult(success=True, result=f"Added: {task}")
            
            elif action == "list":
                items = self._tasks[list_name]
                if not items:
                    return ToolResult(success=True, result=f"No tasks in '{list_name}' list")
                
                lines = [f"# Tasks: {list_name}"]
                for i, item in enumerate(items, 1):
                    status = "✅" if item["done"] else "⬜"
                    lines.append(f"{i}. {status} {item['text']}")
                return ToolResult(success=True, result="\n".join(lines))
            
            elif action == "done":
                try:
                    idx = int(task) - 1
                    if 0 <= idx < len(self._tasks[list_name]):
                        self._tasks[list_name][idx]["done"] = True
                        return ToolResult(success=True, result=f"Marked task {task} as done")
                except ValueError:
                    pass
                return ToolResult(success=False, result=None, error=f"Invalid task number: {task}")
            
            elif action == "remove":
                try:
                    idx = int(task) - 1
                    if 0 <= idx < len(self._tasks[list_name]):
                        removed = self._tasks[list_name].pop(idx)
                        return ToolResult(success=True, result=f"Removed: {removed['text']}")
                except ValueError:
                    pass
                return ToolResult(success=False, result=None, error=f"Invalid task number: {task}")
            
            return ToolResult(success=False, result=None, error=f"Unknown action: {action}")
        
        except Exception as e:
            return ToolResult(success=False, result=None, error=str(e))

    def _get_parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform: 'add', 'list', 'done', or 'remove'",
                },
                "task": {
                    "type": "string",
                    "description": "Task text (for 'add') or task number (for 'done'/'remove')",
                },
                "list_name": {
                    "type": "string",
                    "description": "Name of the todo list (default: 'default')",
                },
            },
            "required": ["action"],
        }
