"""Context manager for token limits with smart compaction."""
import tiktoken
import hashlib
from typing import Optional

DEFAULT_CONTEXT_LIMIT = 16384

# Cache encoding to avoid reloading
_encoder_cache: Optional[tiktoken.Encoding] = None


def _get_encoder() -> tiktoken.Encoding:
    """Get or create cached encoder."""
    global _encoder_cache
    if _encoder_cache is None:
        try:
            _encoder_cache = tiktoken.get_encoding("cl100k_base")
        except Exception:
            return None
    return _encoder_cache


def count_messages_tokens(messages: list, use_cache: bool = True) -> int:
    """Count tokens in messages with caching support."""
    enc = _get_encoder()
    if enc is None:
        return len(str(messages)) // 4

    total = 0
    for msg in messages:
        content = msg.get("content", "")
        role = msg.get("role", "user")
        total += len(enc.encode(content)) + 4
        if role == "system":
            total += 3
    return total


def should_compact(messages: list, threshold: float = 0.8) -> bool:
    """Check if messages should be compacted."""
    return count_messages_tokens(messages) > DEFAULT_CONTEXT_LIMIT * threshold


def compact_messages(messages: list, keep_system: bool = True) -> list:
    """Compact messages to fit within context limit with smart strategy."""
    if not should_compact(messages):
        return messages

    compacted = []
    
    # Always keep system prompt
    if keep_system and messages and messages[0].get("role") == "system":
        compacted.append(messages[0])
        messages = messages[1:]

    # Smart compaction strategy:
    # 1. Keep last 4 messages (recent context)
    # 2. Keep tool results from last 2 interactions
    # 3. Summarize older messages if needed
    
    if len(messages) <= 10:
        compacted.extend(messages)
        return compacted
    
    # Keep last 4 user-assistant pairs
    recent = messages[-8:]
    
    # Also keep any tool result messages in those last 8
    tool_results = [m for m in messages[-12:-8] if m.get("role") == "tool"]
    
    compacted.extend(recent)
    compacted.extend(tool_results)
    
    # If still too large, truncate the oldest messages
    while count_messages_tokens(compacted) > DEFAULT_CONTEXT_LIMIT * 0.6 and len(compacted) > 6:
        # Remove oldest non-system message
        for i in range(1, len(compacted)):
            if compacted[i].get("role") != "system":
                compacted.pop(i)
                break
    
    return compacted


def get_conversation_summary(messages: list) -> str:
    """Generate a brief summary of conversation for context."""
    if len(messages) <= 2:
        return ""
    
    # Simple summary: extract key topics from first few messages
    user_msgs = [m["content"] for m in messages[1:6] if m.get("role") == "user"]
    if not user_msgs:
        return ""
    
    # Just return first 100 chars of first user message as summary
    return f"Earlier: {user_msgs[0][:100]}..."