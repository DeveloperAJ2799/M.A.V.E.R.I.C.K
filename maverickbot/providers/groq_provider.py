"""Groq provider - fast inference with function calling."""
import aiohttp
import json
from typing import List, Dict, Any, Optional
from .base import LLMProvider, LLMResponse


class GroqProvider(LLMProvider):
    """Groq provider - free tier available, fast inference."""

    def __init__(self, model: str = "llama-3.1-70b-versatile", api_key: str = None, **kwargs):
        super().__init__(model)
        self.api_key = api_key or "gsk_placeholder"
        self.base_url = "https://api.groq.com/openai/v1"
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create reusable HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=120),
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
        """Send chat message."""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Convert tools to OpenAI-compatible format
        openai_tools = None
        if tools:
            openai_tools = []
            for tool in tools:
                if 'function' in tool:
                    openai_tools.append(tool)
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if openai_tools:
            payload["tools"] = openai_tools
        
        session = await self._get_session()
        try:
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return LLMResponse(content=f"Error: {error_text}", finish_reason="error")
                
                data = await response.json()
                choice = data["choices"][0]
                message = choice["message"]
                
                content = message.get("content") or ""
                finish_reason = choice.get("finish_reason")
                
                tool_calls = None
                if message.get("tool_calls"):
                    tool_calls = []
                    for tc in message["tool_calls"]:
                        tool_calls.append({
                            "id": tc.get("id", ""),
                            "type": "function",
                            "function": {
                                "name": tc["function"]["name"],
                                "arguments": tc["function"]["arguments"]
                            }
                        })
                
                return LLMResponse(
                    content=content,
                    tool_calls=tool_calls,
                    finish_reason=finish_reason
                )
            
        except Exception as e:
            return LLMResponse(content=f"Error: {str(e)}", finish_reason="error")

    async def list_models(self) -> List[str]:
        return ["llama-3.1-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]

    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None