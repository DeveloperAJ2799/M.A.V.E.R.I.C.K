"""Groq provider - fast inference with function calling."""
import requests
from typing import List, Dict, Any, Optional
from .base import LLMProvider, LLMResponse


class GroqProvider(LLMProvider):
    """Groq provider - free tier available, fast inference."""

    def __init__(self, model: str = "llama-3.1-70b-versatile", api_key: str = None, **kwargs):
        super().__init__(model)
        self.api_key = api_key or "gsk_placeholder"
        self.base_url = "https://api.groq.com/openai/v1"

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
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code != 200:
                return LLMResponse(content=f"Error: {response.text}", finish_reason="error")
            
            data = response.json()
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