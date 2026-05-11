"""UX package for non-technical user experience."""
from maverickbot.ux.user_input import IntentParser, Intent, ActionType
from maverickbot.ux.file_finder import FileFinder, FileCandidate
from maverickbot.ux.confirm import ConfirmationUI, ConfirmationContext, ConfirmationResult
from maverickbot.ux.friendly import FriendlyResponse
from maverickbot.ux.agent import UXAgent, create_ux_agent

__all__ = [
    "IntentParser", "Intent", "ActionType",
    "FileFinder", "FileCandidate",
    "ConfirmationUI", "ConfirmationContext", "ConfirmationResult",
    "FriendlyResponse",
    "UXAgent", "create_ux_agent"
]
