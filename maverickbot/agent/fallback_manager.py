"""Fallback manager for provider switching on errors."""
import asyncio
from typing import List, Optional, Callable, Any
from loguru import logger
from dataclasses import dataclass


@dataclass
class ProviderAttempt:
    """Record of a provider attempt."""
    provider_name: str
    success: bool
    error: Optional[str] = None
    response: Any = None


class FallbackManager:
    """Manages fallback between multiple providers."""

    def __init__(self):
        self._providers: List[tuple] = []  # (name, provider, enabled)
        self._attempts: List[ProviderAttempt] = []
        self._last_successful: Optional[str] = None

    def add_provider(self, name: str, provider, enabled: bool = True):
        """Add a provider to the fallback chain."""
        self._providers.append((name, provider, enabled))
        logger.info(f"Added fallback provider: {name} (enabled: {enabled})")

    def enable_provider(self, name: str):
        """Enable a provider in the fallback chain."""
        for i, (pname, provider, _) in enumerate(self._providers):
            if pname == name:
                self._providers[i] = (pname, provider, True)
                logger.info(f"Enabled fallback provider: {name}")

    def disable_provider(self, name: str):
        """Disable a provider in the fallback chain."""
        for i, (pname, provider, _) in enumerate(self._providers):
            if pname == name:
                self._providers[i] = (pname, provider, False)
                logger.info(f"Disabled fallback provider: {name}")

    def get_enabled_providers(self) -> List[tuple]:
        """Get list of enabled providers in order."""
        return [(name, provider) for name, provider, enabled in self._providers if enabled]

    async def call(
        self,
        func_name: str,
        *args,
        **kwargs
    ) -> Any:
        """Call a method on providers in fallback order."""
        self._attempts = []
        
        enabled = self.get_enabled_providers()
        
        if not enabled:
            raise Exception("No enabled providers available")
        
        last_error = None
        
        for provider_name, provider in enabled:
            try:
                func = getattr(provider, func_name, None)
                if func is None:
                    logger.warning(f"Provider {provider_name} has no method {func_name}")
                    continue
                
                logger.info(f"Trying provider: {provider_name}")
                response = await func(*args, **kwargs)
                
                # Success!
                self._attempts.append(ProviderAttempt(
                    provider_name=provider_name,
                    success=True,
                    response=response
                ))
                self._last_successful = provider_name
                logger.info(f"Successfully used provider: {provider_name}")
                return response
                
            except Exception as e:
                error_str = str(e)
                logger.warning(f"Provider {provider_name} failed: {error_str}")
                
                self._attempts.append(ProviderAttempt(
                    provider_name=provider_name,
                    success=False,
                    error=error_str
                ))
                
                # Check if it's a rate limit - may want to wait and retry
                if "429" in error_str.lower() or "rate limit" in error_str.lower():
                    logger.warning(f"Rate limit hit on {provider_name}, trying next provider...")
                
                last_error = e
                continue
        
        # All providers failed
        raise Exception(f"All providers failed. Last error: {last_error}")

    def get_attempts(self) -> List[ProviderAttempt]:
        """Get list of attempts made."""
        return self._attempts

    def get_last_successful(self) -> Optional[str]:
        """Get the name of the last successful provider."""
        return self._last_successful


def create_fallback_chain(
    nvidia_provider=None,
    lmstudio_provider=None,
    groq_provider=None,
    prefer_nvidia: bool = True,
) -> FallbackManager:
    """Create a fallback chain of providers."""
    manager = FallbackManager()
    
    # Add providers based on preference
    if prefer_nvidia and nvidia_provider:
        manager.add_provider("nvidia", nvidia_provider, enabled=True)
    
    if lmstudio_provider:
        manager.add_provider("lmstudio", lmstudio_provider, enabled=not prefer_nvidia)
    
    if groq_provider:
        manager.add_provider("groq", groq_provider, enabled=False)
    
    # If not preferring NVIDIA, add it last
    if not prefer_nvidia and nvidia_provider:
        manager.add_provider("nvidia", nvidia_provider, enabled=True)
    
    return manager