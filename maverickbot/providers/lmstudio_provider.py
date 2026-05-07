"""LM Studio LLM provider with OpenAI-compatible API."""

import aiohttp
import json
from typing import List, Dict, Any, Optional, AsyncIterator
from .base import LLMProvider, LLMResponse


class LMStudioProvider(LLMProvider):
    """LM Studio API provider with OpenAI-compatible interface."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:1234",
        model: str = "google/gemma-4-e2b",
        **kwargs,
    ):
        super().__init__(model)
        self.base_url = base_url.rstrip("/")
        self.endpoint = f"{self.base_url}/v1/chat/completions"
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
        headers = {"Content-Type": "application/json"}

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        session = await self._get_session()
        async with session.post(self.endpoint, json=payload, headers=headers) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"LM Studio API error ({resp.status}): {error_text}")

            data = await resp.json()
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})

            content = message.get("content", "") or ""
            tool_calls = message.get("tool_calls", None)

            if not tool_calls and content and tools:
                tool_calls = self._extract_tool_calls(content, tools)

            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                finish_reason=choice.get("finish_reason"),
                usage=data.get("usage"),
            )

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
        matches = re.findall(pattern, content, re.DOTALL)
        
        if not matches:
            # Standard <tool_call>format</tool_call>
            pattern = r"<tool_call>\s*(\w+)\s*(\{[^}]+\})?\s*</tool_call>"
            matches = re.findall(pattern, content, re.DOTALL)

        if not matches:
            pattern = r"(\w+)\s*\(\s*(\{[\s\S]*?\})\s*\)"
            matches = re.findall(pattern, content, re.MULTILINE)

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
                except json.JSONDecodeError:
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

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        headers = {"Content-Type": "application/json"}

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        if tools:
            payload["tools"] = tools

        session = await self._get_session()
        async with session.post(self.endpoint, json=payload, headers=headers) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                raise Exception(f"LM Studio API error ({resp.status}): {error_text}")

            async for line in resp.content:
                line = line.decode("utf-8").strip()
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

    async def list_models(self) -> List[str]:
        """List available models from LM Studio."""
        session = await self._get_session()
        try:
            async with session.get(f"{self.base_url}/v1/models") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [m.get("id", "") for m in data.get("data", [])]
        except Exception:
            pass
        return [self.model]