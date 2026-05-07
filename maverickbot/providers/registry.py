"""Provider registry for dynamic provider selection."""
from typing import Dict
from .base import LLMProvider
from .ollama_provider import OllamaProvider
from .lmstudio_provider import LMStudioProvider
from .nvidia_provider import NvidiaProvider
from .openai_provider import OpenAIProvider
from .groq_provider import GroqProvider


class ProviderRegistry:
    _providers: Dict[str, type] = {
        "ollama": OllamaProvider,
        "lmstudio": LMStudioProvider,
        "nvidia": NvidiaProvider,
        "openai": OpenAIProvider,
        "groq": GroqProvider,
    }

    @classmethod
    def create(cls, provider_name: str, **config) -> LLMProvider:
        provider_class = cls._providers.get(provider_name.lower())
        if not provider_class:
            raise ValueError(f"Unknown provider: {provider_name}. Available: {', '.join(cls.list_providers())}")
        return provider_class(**config)

    @classmethod
    def list_providers(cls) -> list:
        return list(cls._providers.keys())