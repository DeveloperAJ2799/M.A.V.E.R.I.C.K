"""M.A.V.E.R.I.C.K configuration schema."""

import os
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class OllamaConfig(BaseModel):
    base_url: str = Field(default="http://localhost:11434", description="Ollama server URL")
    model: str = Field(default="qwen3.5:2b", description="Ollama model name")


class NvidiaConfig(BaseModel):
    api_key: str = Field(default=None, description="NVIDIA API key (or set NVIDIA_API_KEY env var)")
    base_url: str = Field(default="https://integrate.api.nvidia.com/v1", description="NVIDIA NIM endpoint")
    model: str = Field(default="moonshotai/kimi-k2.6", description="NVIDIA model name")
    timeout: int = Field(default=60, description="Request timeout in seconds")

    def get_api_key(self) -> str:
        """Get API key from config or environment."""
        return self.api_key or os.environ.get("NVIDIA_API_KEY", "")


class MCPServerConfig(BaseModel):
    name: str = Field(description="Server name identifier")
    type: str = Field(default="stdio", description="Transport type: stdio or http")
    command: Optional[str] = Field(default=None, description="Command to run (for stdio)")
    args: List[str] = Field(default_factory=list, description="Command arguments")
    env: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    url: Optional[str] = Field(default=None, description="HTTP URL for http transport")
    enabled: bool = Field(default=True, description="Enable this server")


class RateLimitConfig(BaseModel):
    rpm: int = Field(default=36, description="Max requests per minute (40 - 10% safety margin)")
    retry_attempts: int = Field(default=3, description="Number of retry attempts on rate limit")
    retry_backoff: float = Field(default=2.0, description="Exponential backoff base in seconds")


class MaverickConfig(BaseModel):
    temperature: float = Field(default=0.7, description="Temperature for generation")
    max_tokens: int = Field(default=4096, description="Max tokens to generate")
    max_continuations: int = Field(default=3, description="Max times to fetch continuation for truncated responses")
    min_continuation_tokens: int = Field(default=500, description="Min tokens remaining to trigger continuation")
    system_prompt: str = Field(default="You are a helpful AI assistant.", description="System prompt")
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    nvidia: NvidiaConfig = Field(default_factory=NvidiaConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    mcp_servers: Dict[str, MCPServerConfig] = Field(default_factory=dict, description="MCP servers configuration")