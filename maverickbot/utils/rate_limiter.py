"""Rate limiter for NVIDIA API - Stay under 40 RPM."""
import asyncio
import time
import os
from typing import Optional, Callable, Any
from loguru import logger
from dataclasses import dataclass, field


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    max_requests_per_minute: int = 36  # 40 - 10% safety margin = 36
    retry_attempts: int = 3
    retry_backoff_base: float = 2.0  # seconds
    min_interval: float = 1.6  # seconds between requests (36 RPM = 1.67s)
    queue_timeout: int = 120  # max seconds to wait in queue


class RateLimiter:
    """Token bucket rate limiter for NVIDIA API."""

    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        
        # Token bucket state
        self._tokens = self.config.max_requests_per_minute
        self._last_refill = time.time()
        self._lock = asyncio.Lock()
        
        # Queue for pending requests
        self._queue: asyncio.Queue = asyncio.Queue()
        self._processing = False
        
        # Stats
        self._total_requests = 0
        self._total_429_errors = 0
        self._total_successful = 0

    def _refill_tokens(self):
        """Refill tokens based on time elapsed."""
        now = time.time()
        elapsed = now - self._last_refill
        
        # Refill tokens: (elapsed_seconds / 60) * max_requests_per_minute
        refill_amount = (elapsed / 60) * self.config.max_requests_per_minute
        self._tokens = min(
            self.config.max_requests_per_minute,
            self._tokens + refill_amount
        )
        self._last_refill = now

    async def acquire(self, timeout: float = None) -> bool:
        """Acquire a token for API request. Returns True if acquired."""
        timeout = timeout or self.config.queue_timeout
        
        start_time = time.time()
        
        while True:
            async with self._lock:
                self._refill_tokens()
                
                if self._tokens >= 1:
                    self._tokens -= 1
                    self._total_requests += 1
                    return True
                
                # Calculate wait time
                tokens_needed = 1 - self._tokens
                wait_time = (tokens_needed / self.config.max_requests_per_minute) * 60
            
            # Check timeout
            if time.time() - start_time > timeout:
                logger.warning(f"Rate limiter timeout after {timeout}s")
                return False
            
            # Wait before retrying
            await asyncio.sleep(min(wait_time, 1.0))

    async def call_with_rate_limit(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Call a function with rate limiting and retry logic."""
        last_error = None
        
        for attempt in range(self.config.retry_attempts):
            # Acquire token
            if not await self.acquire():
                raise Exception("Rate limit timeout - could not acquire token")
            
            try:
                result = await func(*args, **kwargs)
                self._total_successful += 1
                return result
                
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                
                # Check for rate limit (429)
                if "429" in error_str or "rate limit" in error_str:
                    self._total_429_errors += 1
                    logger.warning(f"NVIDIA rate limit hit (attempt {attempt + 1}/{self.config.retry_attempts})")
                    
                    # Exponential backoff
                    wait_time = self.config.retry_backoff_base ** attempt
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                    continue
                
                # Non-rate-limit error - fail immediately
                raise
        
        # All retries exhausted
        raise Exception(f"NVIDIA API failed after {self.config.retry_attempts} attempts: {last_error}")

    def get_stats(self) -> dict:
        """Get rate limiter statistics."""
        return {
            "total_requests": self._total_requests,
            "successful": self._total_successful,
            "rate_limited_429": self._total_429_errors,
            "success_rate": f"{(self._total_successful / max(1, self._total_requests)) * 100:.1f}%",
            "current_tokens": f"{self._tokens:.2f}",
            "config": {
                "max_rpm": self.config.max_requests_per_minute,
                "min_interval": self.config.min_interval,
            }
        }


class RateLimitedProvider:
    """Wrapper to add rate limiting to any provider."""

    def __init__(self, provider, rate_limiter: RateLimiter = None):
        self.provider = provider
        self.rate_limiter = rate_limiter or RateLimiter()

    async def chat(self, *args, **kwargs):
        """Chat with rate limiting."""
        return await self.rate_limiter.call_with_rate_limit(
            self.provider.chat,
            *args,
            **kwargs
        )

    async def chat_stream(self, *args, **kwargs):
        """Stream chat with rate limiting."""
        return await self.rate_limiter.call_with_rate_limit(
            self.provider.chat_stream,
            *args,
            **kwargs
        )

    async def close(self):
        """Close the underlying provider."""
        if hasattr(self.provider, 'close'):
            await self.provider.close()


# Global rate limiter instance
_global_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter(config: RateLimitConfig = None) -> RateLimiter:
    """Get or create global rate limiter."""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter(config)
    return _global_rate_limiter


def set_rate_limiter(limiter: RateLimiter):
    """Set global rate limiter."""
    global _global_rate_limiter
    _global_rate_limiter = limiter