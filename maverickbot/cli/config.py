"""CLI configuration management."""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from loguru import logger


DEFAULT_CONFIG_PATHS = [
    Path.cwd() / "maverickbot.yaml",
    Path.cwd() / "maverickbot.yml",
    Path.home() / ".maverickbot" / "config.yaml",
]


@dataclass
class CLIConfig:
    """CLI configuration."""
    provider: str = "lmstudio"
    model: str = "llama-3.1-8b"
    lmurl: str = "http://127.0.0.1:1234"
    temperature: float = 0.7
    max_tokens: int = 4096
    system_prompt: str = "You are a helpful AI assistant with access to tools."
    multi_agent: bool = False
    debug: bool = False
    log_level: str = "ERROR"
    plugins_dir: Optional[str] = None
    skills_dir: Optional[str] = None
    session_persist: bool = True
    session_file: str = ".maverickbot_session.json"
    mcp_servers: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    nvidia_api_key: str = ""


class ConfigManager:
    """Manage CLI configuration from files and env vars."""

    def __init__(self):
        self.config = CLIConfig()
        self._loaded = False

    def load(self, config_file: Optional[str] = None) -> CLIConfig:
        """Load configuration from file and environment variables."""
        if self._loaded:
            return self.config

        if config_file:
            self._load_from_file(Path(config_file))
        else:
            for path in DEFAULT_CONFIG_PATHS:
                if path.exists():
                    self._load_from_file(path)
                    break

        self._load_from_env()
        self._loaded = True
        return self.config

    def _load_from_file(self, path: Path):
        """Load config from YAML file."""
        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f) or {}

            for key, value in data.items():
                if key == "mcp_servers" and isinstance(value, dict):
                    self.config.mcp_servers = value
                elif hasattr(self.config, key):
                    setattr(self.config, key, value)

            logger.info(f"Loaded config from {path}")
        except Exception as e:
            logger.warning(f"Failed to load config from {path}: {e}")

    def _load_from_env(self):
        """Load config from environment variables."""
        env_mappings = {
            "MAVERICK_PROVIDER": ("provider", str),
            "MAVERICK_MODEL": ("model", str),
            "MAVERICK_URL": ("lmurl", str),
            "MAVERICK_TEMPERATURE": ("temperature", float),
            "MAVERICK_MAX_TOKENS": ("max_tokens", int),
            "MAVERICK_DEBUG": ("debug", bool),
            "MAVERICK_LOG_LEVEL": ("log_level", str),
            "MAVERICK_MULTI_AGENT": ("multi_agent", bool),
        }

        for env_var, (attr, type_fn) in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                try:
                    if type_fn == bool:
                        value = value.lower() in ("true", "1", "yes")
                    else:
                        value = type_fn(value)
                    setattr(self.config, attr, value)
                except ValueError:
                    logger.warning(f"Invalid value for {env_var}: {value}")

    def save(self, path: Path = None):
        """Save current config to file."""
        path = path or DEFAULT_CONFIG_PATHS[0]
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w") as f:
            data = {
                "provider": self.config.provider,
                "model": self.config.model,
                "lmurl": self.config.lmurl,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "system_prompt": self.config.system_prompt,
                "multi_agent": self.config.multi_agent,
                "log_level": self.config.log_level,
            }
            yaml.dump(data, f, default_flow_style=False)
        
        logger.info(f"Saved config to {path}")

    def update(self, **kwargs):
        """Update config values."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)