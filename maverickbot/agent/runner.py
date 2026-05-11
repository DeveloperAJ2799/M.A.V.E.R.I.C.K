"""Agent runner for managing the agent execution."""

from typing import Optional, Dict, Any, List
from loguru import logger

from ..providers.base import LLMProvider
from .loop import AgentLoop
from .session import SessionManager
from .tools.registry import ToolRegistry
from .context_manager import (
    should_compact,
    compact_messages,
    count_messages_tokens,
    DEFAULT_CONTEXT_LIMIT,
)
from .fallback_manager import FallbackManager, create_fallback_chain
from .workflow import WorkflowPlanner, create_auto_execute_loop


class AgentRunner:
    """Main agent runner that coordinates all components."""

    def __init__(
        self,
        provider: LLMProvider,
        tool_registry: ToolRegistry,
        system_prompt: str = "You are a helpful AI assistant.",
        fallback_providers: List[LLMProvider] = None,
        fallback_names: List[str] = None,
        auto_workflow: bool = True,
    ):
        self.primary_provider = provider
        self.tool_registry = tool_registry
        self.system_prompt = system_prompt
        self.session_manager = SessionManager()
        self.auto_workflow = auto_workflow
        
        # Setup fallback chain
        self.fallback_manager = None
        if fallback_providers and fallback_names:
            self.fallback_manager = create_fallback_chain(
                nvidia_provider=fallback_providers[0] if fallback_names[0] == "nvidia" else None,
                lmstudio_provider=fallback_providers[0] if fallback_names[0] == "lmstudio" else None,
                groq_provider=fallback_providers[0] if fallback_names[0] == "groq" else None,
                prefer_nvidia=True,
            )
            # Use primary as first provider
            self.fallback_manager._providers = [(fallback_names[0], fallback_providers[0], True)] + [
                (n, p, e) for n, p, e in self.fallback_manager._providers if n != fallback_names[0]
            ]
        
        # Get active provider (prefer fallback if available)
        self.provider = self.fallback_manager.get_enabled_providers()[0][1] if self.fallback_manager else provider
        
        self.loop = AgentLoop(provider=self.provider, tool_registry=tool_registry)
        
        # Auto workflow planning
        if auto_workflow:
            self.auto_loop = create_auto_execute_loop(self.loop)
            self._workflow_planner = WorkflowPlanner(tool_registry, self.provider)
        else:
            self.auto_loop = None
            self._workflow_planner = None

        self.session_manager.create_session(system_prompt=system_prompt)

    async def chat(
        self, user_input: str, temperature: float = 0.7, max_tokens: int = 4096, skip_workflow: bool = False
    ) -> str:
        session = self.session_manager.get_current_session()
        if not session:
            session = self.session_manager.create_session(
                system_prompt=self.system_prompt
            )

        session.add_message(role="user", content=user_input)
        messages = session.get_messages()

        token_count = count_messages_tokens(messages)
        # Trigger compaction only when approaching limit (80% = ~13,000 tokens)
        if token_count > int(DEFAULT_CONTEXT_LIMIT * 0.80):
            print(f"[Auto-compacting session ({token_count} tokens)...]")
            compacted = compact_messages(messages)
            session.replace_messages(compacted)
            messages = session.get_messages()

        # Use auto workflow if enabled and not explicitly skipped
        if self.auto_loop and not skip_workflow and not user_input.startswith("!noworkflow") and not user_input.startswith("!plan"):
            try:
                response = await self.auto_loop.process_message(messages=messages)
            except Exception as e:
                logger.warning(f"Auto workflow failed: {e}, falling back to direct")
                response = await self.loop.process_message(messages=messages)
        elif self.fallback_manager:
            try:
                response = await self.fallback_manager.call(
                    "process_message",
                    messages=messages,
                )
            except Exception as e:
                logger.error(f"All providers failed: {e}")
                raise
        else:
            try:
                response = await self.loop.process_message(messages=messages)
            except Exception as e:
                # If timeout/error, try with compacted session
                if "timeout" in str(e).lower() or "rate limit" in str(e).lower():
                    print(f"[Retry with compacted session after error: {e}]")
                    current_msgs = session.get_messages()
                    compacted = compact_messages(current_msgs)
                    session.replace_messages(compacted)
                    messages = session.get_messages()
                    response = await self.loop.process_message(messages=messages)
                else:
                    raise

        session.add_message(role="assistant", content=response)

        messages = session.get_messages()
        token_count = count_messages_tokens(messages)
        if should_compact(messages):
            print(f"[Warning: Session approaching limit ({token_count} tokens)]")

        return response

    async def chat_stream(
        self, user_input: str, temperature: float = 0.7, max_tokens: int = 4096
    ) -> str:
        session = self.session_manager.get_current_session()
        if not session:
            session = self.session_manager.create_session(
                system_prompt=self.system_prompt
            )

        session.add_message(role="user", content=user_input)
        messages = session.get_messages()

        full_content = ""
        async for chunk in self.loop.chat_stream(messages=messages):
            full_content += chunk

        session.add_message(role="assistant", content=full_content)
        return full_content

    def reset(self) -> None:
        session = self.session_manager.get_current_session()
        if session:
            session.clear()

    def get_session_info(self) -> Dict[str, Any]:
        session = self.session_manager.get_current_session()
        if not session:
            return {}
        return {
            "id": session.id,
            "message_count": len(session.messages),
            "system_prompt": session.system_prompt,
        }

    async def close(self):
        """Clean up resources."""
        if self.fallback_manager:
            for name, provider in self.fallback_manager.get_enabled_providers():
                if hasattr(provider, 'close'):
                    await provider.close()
        elif hasattr(self.provider, 'close'):
            await self.provider.close()