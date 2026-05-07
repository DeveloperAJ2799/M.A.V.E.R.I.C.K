"""OpenAI provider with native function calling."""
import openai
from typing import List, Dict, Any, Optional
from .base import LLMProvider, LLMResponse


class OpenAIProvider(LLMProvider):
    """OpenAI provider using the OpenAI API with native function calling."""

    def __init__(self, model: str = "gpt-4", api_key: str = None, base_url: str = None, **kwargs):
        super().__init__(model)
        self.client = openai.OpenAI(
            api_key=api_key or openai.api_key,
            base_url=base_url or "https://api.openai.com/v1"
        )
        self.default_headers = {
            "Content-Type": "application/json",
        }

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        """Send chat message with optional function calling."""
        
        # Convert tools to OpenAI format
        openai_tools = None
        if tools:
            openai_tools = []
            for tool in tools:
                if 'function' in tool:
                    openai_tools.append(tool)
        
        # Make API call
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=openai_tools,
            )
            
            # Extract response
            choice = response.choices[0]
            content = choice.message.content or ""
            finish_reason = choice.finish_reason
            
            # Extract tool calls if present
            tool_calls = None
            if choice.message.tool_calls:
                tool_calls = []
                for tc in choice.message.tool_calls:
                    tool_calls.append({
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    })
            
            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                finish_reason=finish_reason,
                usage={"prompt_tokens": response.usage.prompt_tokens, "completion_tokens": response.usage.completion_tokens} if response.usage else None
            )
            
        except Exception as e:
            return LLMResponse(
                content=f"Error: {str(e)}",
                tool_calls=None,
                finish_reason="error"
            )

    async def list_models(self) -> List[str]:
        """List available models."""
        try:
            models = self.client.models.list()
            return [m.id for m in models.data]
        except Exception:
            # Return default models if API fails
            return ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]