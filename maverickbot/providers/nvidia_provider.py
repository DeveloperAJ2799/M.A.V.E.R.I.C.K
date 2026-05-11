"""NVIDIA NIM Provider - OpenAI-compatible API with rate limiting."""
import os
import asyncio
import aiohttp
import json
from typing import List, Dict, Any, Optional
from loguru import logger

from .base import LLMProvider, LLMResponse


class NvidiaProvider(LLMProvider):
    """NVIDIA NIM provider using OpenAI-compatible API."""

    def __init__(
        self,
        model: str = "meta/llama-3.1-70b-instruct",
        api_key: str = None,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        timeout: int = 300,
        max_retries: int = 3,
        **kwargs
    ):
        super().__init__(model)
        self.api_key = api_key or os.environ.get("NVIDIA_API_KEY")
        if not self.api_key:
            raise ValueError("NVIDIA_API_KEY not found. Set it via environment variable or config.")
        
        self.base_url = base_url.rstrip("/")
        self.endpoint = f"{self.base_url}/chat/completions"
        self.timeout_seconds = timeout
        self.max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create reusable HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout_seconds),
                connector=aiohttp.TCPConnector(limit=10, keepalive_timeout=30)
            )
        return self._session

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """Send chat message with optional function calling."""
        
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        session = await self._get_session()
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                async with session.post(
                    self.endpoint, 
                    json=payload, 
                    headers=headers
                ) as resp:
                    
                    if resp.status == 429:
                        if attempt < self.max_retries - 1:
                            wait_time = 2 ** attempt
                            logger.warning(f"Rate limited, retrying in {wait_time}s...")
                            await asyncio.sleep(wait_time)
                            continue
                        raise Exception("Rate limit exceeded (429)")
                    
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise Exception(f"NVIDIA API error ({resp.status}): {error_text}")

                    data = await resp.json()
                    
                    if 'error' in data:
                        raise Exception(f"NVIDIA API error: {data['error']}")
                    
                    # Handle the response similar to OpenAI
                    choice = data.get("choices", [{}])[0]
                    message = choice.get("message", {})
                    
                    content = message.get("content", "") or ""
                    tool_calls = message.get("tool_calls", None)
                    
                    # Extract tool calls if present
                    if not tool_calls and tools and content:
                        tool_calls = self._extract_tool_calls(content, tools)

                    return LLMResponse(
                        content=content,
                        tool_calls=tool_calls,
                        finish_reason=choice.get("finish_reason"),
                        usage=data.get("usage"),
                    )
                    
            except asyncio.TimeoutError:
                last_error = f"NVIDIA API timeout after {self.timeout_seconds}s"
                logger.warning(f"Timeout (attempt {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
            except aiohttp.ClientError as e:
                last_error = f"NVIDIA API connection error: {str(e)}"
                logger.warning(f"Connection error (attempt {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
            except Exception as e:
                last_error = str(e)
                logger.error(f"Unexpected error: {e}")
                raise
        
        raise Exception(last_error or "Max retries exceeded")

    def _extract_tool_calls(
        self, content: str, tools: List[Dict[str, Any]]
    ) -> Optional[List[Dict[str, Any]]]:
        """Extract tool calls from content using regex."""
        import re
        
        tool_names = [
            t.get("function", {}).get("name", "")
            for t in tools
            if t.get("function", {}).get("name")
        ]
        
        # Handle <|tool_call>call:tool_name{...}
        pattern = r"<\|tool_call>\s*call:(\w+)\s*(\{[\s\S]*?\})"
        matches = re.findall(pattern, content)
        
        if not matches:
            return None
        
        tool_calls = []
        for idx, (tool_name, args_str) in enumerate(matches):
            if tool_name in tool_names:
                try:
                    args = json.loads(args_str)
                except:
                    args = {"input": args_str}
                    
                tool_calls.append({
                    "id": f"call_{idx}_{tool_name}",
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(args) if isinstance(args, dict) else args_str
                    }
                })
        
        return tool_calls if tool_calls else None

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict[str, Any]]] = None,
    ):
        """Stream chat response - not implemented for requests."""
        # For streaming, we'd need to set stream: True in payload
        # and iterate over the response stream.
        # Just do non-streaming for now as per base implementation
        result = await self.chat(messages, temperature, max_tokens, tools)
        yield result.content

    async def list_models(self) -> List[str]:
        """List available models."""
        return [
            "meta/llama-3.1-70b-instruct",
            "meta/llama-3.1-405b-instruct",
            "mistralai/mistral-7b-instruct-v0.3",
            "nvidia/llama-3.1-nemotron-70b-instruct",
        ]

    async def close(self):
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None