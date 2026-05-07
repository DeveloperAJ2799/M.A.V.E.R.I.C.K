"""Ollama LLM provider."""
import aiohttp
import json
import re
from typing import List, Dict, Any, Optional
from .base import LLMProvider, LLMResponse


class OllamaProvider(LLMProvider):
    """Ollama API provider."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen3.5:2b",
        **kwargs,
    ):
        super().__init__(model)
        self.base_url = base_url.rstrip("/")
        self.endpoint = f"{self.base_url}/api/chat"
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create reusable HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=120),
                connector=aiohttp.TCPConnector(limit=10, keepalive_timeout=30)
            )
        return self._session

    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "options": {"num_predict": max_tokens},
        }

        session = await self._get_session()
        async with session.post(self.endpoint, json=payload) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"Ollama API error ({resp.status}): {error_text}")

            data = await resp.json()
            message = data.get("message", {})

            content = message.get("content", "") or ""
            tool_calls = None

            if not message.get("tool_calls") and content and tools:
                tool_calls = self._extract_tool_calls(content, tools)

            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                finish_reason=data.get("done_reason"),
            )

    def _extract_tool_calls(
        self, content: str, tools: List[Dict[str, Any]]
    ) -> Optional[List[Dict[str, Any]]]:
        """Extract tool calls from content using regex."""
        tool_names = [
            t.get("function", {}).get("name", "")
            for t in tools
            if t.get("function", {}).get("name")
        ]

        patterns = [
            r"<tool_call>\s*(\w+)\s*(\{[^}]+\})?\s*</tool_call>",
            r"(\w+)\s*\(\s*(\{[\s\S]*?\})\s*\)",
            r"(\w+)\((^\)]+)\)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
            if matches:
                break

        if not matches:
            return None

        extracted = []
        for func_name, args_str in matches:
            if func_name in tool_names:
                try:
                    args = (
                        json.loads(args_str)
                        if args_str.strip().startswith("{")
                        else {"input": args_str}
                    )
                except (json.JSONDecodeError, KeyError):
                    args = {"input": args_str}

                extracted.append(
                    {
                        "id": f"call_{len(extracted)}",
                        "type": "function",
                        "function": {
                            "name": func_name,
                            "arguments": json.dumps(args),
                        },
                    }
                )

        return extracted if extracted else None

    async def list_models(self) -> List[str]:
        """List available models from Ollama."""
        session = await self._get_session()
        try:
            async with session.get(f"{self.base_url}/api/tags") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            pass
        return [self.model]