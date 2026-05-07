"""Subagent for specialized tasks."""


class Subagent:
    """Subagent for running specialized tasks."""

    def __init__(self, name: str, system_prompt: str):
        self.name = name
        self.system_prompt = system_prompt

    async def run(self, task: str):
        """Run a task."""
        return f"Subagent {self.name} completed: {task}"