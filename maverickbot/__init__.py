"""M.A.V.E.R.I.C.K v2.0 - AI agent with plugin, skill & multi-agent system."""
import os
from pathlib import Path

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

from maverickbot.cli.runner import main
from maverickbot.core import Registry, PluginLoader, SkillManager
from maverickbot.multiagent import MultiAgentOrchestrator

__all__ = ["main", "Registry", "PluginLoader", "SkillManager", "MultiAgentOrchestrator"]