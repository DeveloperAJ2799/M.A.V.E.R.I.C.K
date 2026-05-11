"""Agent loop with tool execution."""

import json
import asyncio
import hashlib
import threading
import time
from typing import List, Dict, Any, Optional
from collections import OrderedDict
from loguru import logger

from ..providers.base import LLMProvider
from .tools.registry import ToolRegistry


class _ThinkingSpinner:
    """Internal spinner for thinking state."""
    
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
    """Internal process bar for tool execution."""
    
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


class LRUCache:
    """Simple LRU cache with TTL support."""
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self.cache: OrderedDict = OrderedDict()
        self.max_size = max_size
        self.ttl = ttl_seconds
    
    def _make_key(self, tool_name: str, args: Dict) -> str:
        key_data = f"{tool_name}:{json.dumps(args, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, tool_name: str, args: Dict) -> Optional[Any]:
        key = self._make_key(tool_name, args)
        if key in self.cache:
            value, timestamp = self.cache[key]
            if asyncio.get_event_loop().time() - timestamp < self.ttl:
                self.cache.move_to_end(key)
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, tool_name: str, args: Dict, value: Any):
        key = self._make_key(tool_name, args)
        timestamp = asyncio.get_event_loop().time()
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = (value, timestamp)
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)
    
    def clear(self):
        self.cache.clear()


class AgentLoop:
    """Main agent loop for processing messages and executing tools."""

    def __init__(
        self,
        provider: LLMProvider,
        tool_registry: ToolRegistry,
        max_tool_calls: int = 10,
    ):
        self.provider = provider
        self.tool_registry = tool_registry
        self.max_tool_calls = max_tool_calls
        self._tool_cache = LRUCache(max_size=50, ttl_seconds=300)
        self._cached_schemas: Optional[List[Dict[str, Any]]] = None
        self._schemas_hash: Optional[str] = None

    def _get_schemas_cached(self) -> List[Dict[str, Any]]:
        """Get tool schemas with caching."""
        schemas = self.tool_registry.get_schemas()
        if not schemas:
            return []
        
        current_hash = hashlib.md5(json.dumps(schemas, sort_keys=True).encode()).hexdigest()
        
        if self._cached_schemas is None or self._schemas_hash != current_hash:
            self._cached_schemas = schemas
            self._schemas_hash = current_hash
        
        return self._cached_schemas

    def _should_continue(self, response, min_chars: int = 50) -> bool:
        """Check if response needs continuation."""
        content = response.content or ""
        content_len = len(content)
        
        # For responses > 300 chars without proper ending, continue
        if content_len > 300:
            last_char = content.rstrip()[-1] if content.rstrip() else ''
            proper_endings = ('.','!','?')
            
            if last_char not in proper_endings:
                return True
        
        # Check standard truncation indicators  
        truncation_indicators = {None, "length", "max_tokens", "stop", "eos"}
        if response.finish_reason in truncation_indicators and content_len > min_chars:
            return True
        
        return False

    async def _continue_response(self, messages: List[Dict[str, str]], content: str) -> str:
        """Get continuation of truncated response silently."""
        max_continuations = 15
        continuation_count = 0
        full_content = content
        
        while continuation_count < max_continuations:
            messages.append({"role": "user", "content": "Continue your previous response. Complete the sentence or paragraph you were writing. Do not summarize or restart."})
            
            spinner = _ThinkingSpinner()
            spinner.start()
            try:
                continuation = await self.provider.chat(messages=messages, max_tokens=8192)
            finally:
                spinner.stop()
            
            if not continuation.content:
                break
            
            full_content += " " + continuation.content
            messages.append({"role": "assistant", "content": continuation.content})
            
            # Only stop if response ends with proper punctuation AND not truncated
            last_char = full_content.rstrip()[-1] if full_content.rstrip() else ''
            proper_endings = ('.','!','?')
            is_truncated = continuation.finish_reason in {None, "length", "max_tokens"}
            
            # Stop if: proper ending AND not truncated
            if last_char in proper_endings and not is_truncated:
                break
            
            continuation_count += 1
        
        return full_content

    async def process_message(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = None,
    ) -> str:
        tool_schemas = self._get_schemas_cached()
        all_new_tool_results = []
        tool_calls_iteration = 0
        final_text_content = ""

        while tool_calls_iteration < self.max_tool_calls:
            spinner = _ThinkingSpinner()
            spinner.start()
            try:
                response = await self.provider.chat(
                    messages=messages,
                    tools=tool_schemas if tool_schemas else None,
                )
            finally:
                spinner.stop()

            # Check if response was truncated and needs continuation
            content = response.content if response.content else ""
            if self._should_continue(response):
                content = await self._continue_response(messages, content)

            if not response.tool_calls:
                final_text_content = content
                break

            # Add assistant message with tool calls to history
            messages.append(
                {
                    "role": "assistant",
                    "content": content,
                    "tool_calls": response.tool_calls,
                }
            )

            # Execute tool calls IN PARALLEL
            tool_call_tasks = [
                self._execute_tool(tool_call)
                for tool_call in response.tool_calls
            ]
            new_tool_messages = await asyncio.gather(*tool_call_tasks)

            # Append results to messages in deterministic order
            iteration_results = []
            for tool_msg in new_tool_messages:
                messages.append(tool_msg)
                iteration_results.append(tool_msg["content"])
                all_new_tool_results.append(tool_msg["content"])

            # If any tool failed with a critical error, we might want to stop, 
            # but usually we let the LLM see the error and decide.
            # For now, preserve the original behavior of returning errors if they occur.
            failed_results = [r for r in iteration_results if r.startswith("Error:")]
            if failed_results:
                # If we have successful results too, maybe we should continue?
                # The original code returned immediately on any error.
                return "\n".join(iteration_results)

            tool_calls_iteration += 1

        # Combine ONLY the tool results from this entire process_message call with the final content
        tool_results_combined = "\n".join(all_new_tool_results)
        
        if tool_results_combined and final_text_content:
            return f"{tool_results_combined}\n\n{final_text_content}"
        elif tool_results_combined:
            return tool_results_combined
        else:
            return final_text_content

    async def _execute_tool(
        self, tool_call: Dict[str, Any]
    ) -> Dict[str, str]:
        func = tool_call.get("function", {})
        tool_name = func.get("name")
        arguments = func.get("arguments", "{}")

        # Handle placeholder tool names
        if not tool_name or tool_name == "function_name" or tool_name == "unknown":
            logger.warning(f"Invalid tool name from model: {tool_name}")
            return {
                "role": "tool",
                "tool_call_id": tool_call.get("id"),
                "content": "Error: Invalid tool name specified",
            }

        try:
            if isinstance(arguments, str):
                args = json.loads(arguments)
            else:
                args = arguments
        except json.JSONDecodeError:
            args = {"input": str(arguments)}

        logger.debug(f"Executing tool: {tool_name} with args: {args}")

        # Check cache first for read-only tools
        cacheable_tools = {"read_file", "read_pdf", "read_docx", "read_xlsx", "read_csv", "system_info", "git_status", "git_log", "grep", "glob", "list_mcp_servers"}
        if tool_name in cacheable_tools:
            cached_result = self._tool_cache.get(tool_name, args)
            if cached_result is not None:
                logger.debug(f"Tool cache hit: {tool_name}")
                return {
                    "role": "tool",
                    "tool_call_id": tool_call.get("id"),
                    "content": cached_result,
                }

        # Show process bar during tool execution
        process_bar = _ProcessBar(tool_name)
        process_bar.start()
        try:
            result = await self.tool_registry.execute(tool_name, **args)
        finally:
            process_bar.stop(success=result.success)
        
        result_content = result.result if result.success else f"Error: {result.error}"

        # Cache successful results for read-only tools
        if tool_name in cacheable_tools and result.success:
            self._tool_cache.set(tool_name, args, result_content)
        
        return {
            "role": "tool",
            "tool_call_id": tool_call.get("id"),
            "content": result_content,
        }

    async def chat_stream(self, messages: List[Dict[str, str]]) -> str:
        """Process message and yield streaming response."""
        tool_schemas = self.tool_registry.get_schemas()

        full_content = ""
        async for chunk in self.provider.chat_stream(
            messages=messages,
            tools=tool_schemas if tool_schemas else None,
        ):
            full_content += chunk
            yield chunk

        messages.append({"role": "assistant", "content": full_content})
